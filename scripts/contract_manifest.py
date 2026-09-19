#!/usr/bin/env python3
"""Generate and verify ``contracts/manifest.json``.

The manifest is the record of which contracts are frozen, who owns them, and
what their content hash was at freeze time. Schema drift means a file changed
without a reviewed revision -- ``--check`` fails CI on exactly that.

Usage:
    python scripts/contract_manifest.py --check    # CI: fail on drift
    python scripts/contract_manifest.py --update   # after a REVIEWED change

Standard library only, so it runs before any dependency is installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "contracts" / "manifest.json"

#: The current revision. B00 starts at a draft; it is replaced by the actual
#: approved revision once contract review completes. No final v2 executable
#: contract is assumed to exist.
REVISION = "school-contracts-v3-draft"

#: id -> slug, duplicated here deliberately: this script must run without the
#: backend package importable (for example in a lint-only CI job).
MODULE_SLUGS = {
    "M00": "demo",
    "M01": "access",
    "M02": "registry",
    "M03": "timetable",
    "M04": "attendance",
    "M05": "assessment",
    "M06": "performance",
    "M07": "fees",
    "M08": "transport",
    "M09": "library",
    "M10": "alumni",
    "M11": "communications",
    "M12": "files",
    "M13": "exchange",
    "M14": "platform",
}

#: Contract owners. The foundation owns the shared envelopes; a module owns its
#: own API and events. An owner is who must review a revision.
FOUNDATION_OWNER = "foundation (B00)"


def sha256_of(path: pathlib.Path) -> str:
    """Return the SHA-256 of a file's bytes.

    Hashes raw bytes rather than parsed JSON, so a reformat is also flagged. A
    reformat is a real change to a file other systems may parse.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: pathlib.Path) -> str:
    """Return a repo-relative POSIX path for stable manifest content."""
    return path.relative_to(REPO_ROOT).as_posix()


def build_manifest() -> dict:
    """Assemble the manifest from what is actually on disk.

    Deliberately derives entries from the filesystem instead of a hand-kept
    list, so a new schema file cannot be silently omitted from the manifest.

    Does not handle: deciding whether a contract *should* be frozen. That is a
    human review gate; this records the outcome.
    """
    common_dir = REPO_ROOT / "contracts" / "common"
    common_entries = []
    for path in sorted(common_dir.glob("*.schema.json")):
        common_entries.append(
            {
                "id": f"common/{path.name.removesuffix('.schema.json')}",
                "path": relative(path),
                "sha256": sha256_of(path),
                "owner": FOUNDATION_OWNER,
                "kind": "json-schema",
                "frozen": True,
            }
        )

    modules: dict[str, dict] = {}
    for module_id, slug in sorted(MODULE_SLUGS.items()):
        module_dir = REPO_ROOT / "contracts" / module_id
        artefacts = []
        for pattern in ("openapi.yaml", "openapi.json", "*.schema.json"):
            for path in sorted(module_dir.glob(pattern)):
                artefacts.append(
                    {
                        "id": f"{module_id}/{path.name}",
                        "path": relative(path),
                        "sha256": sha256_of(path),
                        "owner": f"{module_id} {slug}",
                        "kind": "openapi" if path.name.startswith("openapi") else "json-schema",
                        "frozen": module_id == "M00",
                    }
                )
        fixtures = []
        for path in sorted((module_dir / "fixtures").glob("*.json")):
            fixtures.append(
                {
                    "id": f"{module_id}/fixtures/{path.name}",
                    "path": relative(path),
                    "sha256": sha256_of(path),
                    "owner": f"{module_id} {slug}",
                    "kind": "consumer-fixture",
                    "frozen": module_id == "M00",
                }
            )

        packet = module_dir / "PACKET.md"
        modules[module_id] = {
            "slug": slug,
            # M00 is the placeholder: its contract is generated from real code
            # and frozen so drift is detectable. The fourteen business modules
            # are not started; nothing about them is frozen yet.
            "status": "frozen" if module_id == "M00" else "not_started",
            "packet": relative(packet) if packet.exists() else None,
            "artefacts": artefacts,
            "fixtures": fixtures,
        }

    return {
        "revision": REVISION,
        "status": "draft",
        "note": (
            "Starting revision for the B00 foundation. No final v2 executable "
            "contract is assumed to exist. Replace 'revision' with the actual "
            "approved revision once contract review completes, and flip an "
            "entry's 'frozen' to true only after its human review gate."
        ),
        "envelope_versions": {"event_envelope": 1},
        "common": common_entries,
        "modules": modules,
    }


def render(manifest: dict) -> str:
    """Serialise the manifest deterministically.

    Sorted keys and a trailing newline, so regenerating on an unchanged tree
    produces a byte-identical file and the diff is always meaningful.
    """
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"


def main() -> int:
    """Run --check or --update. Returns a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail if the manifest is stale")
    group.add_argument("--update", action="store_true", help="rewrite the manifest")
    arguments = parser.parse_args()

    expected = render(build_manifest())

    if arguments.update:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(expected)
        print(f"wrote {relative(MANIFEST_PATH)} at revision {REVISION}")
        return 0

    if not MANIFEST_PATH.exists():
        print(f"FAIL: {relative(MANIFEST_PATH)} does not exist", file=sys.stderr)
        print("      run: python scripts/contract_manifest.py --update", file=sys.stderr)
        return 1

    actual = MANIFEST_PATH.read_text()
    if actual != expected:
        print("FAIL: contract schema drift detected.", file=sys.stderr)
        print(
            "      A contract file changed without the manifest being updated.\n"
            "      This is a reviewed-revision gate, not a formatting nit: if the\n"
            "      change is intended, get it reviewed and run\n"
            "        python scripts/contract_manifest.py --update",
            file=sys.stderr,
        )
        _report_differences(json.loads(actual), json.loads(expected))
        return 1

    frozen = sum(1 for entry in _all_entries(json.loads(actual)) if entry.get("frozen"))
    print(f"OK: manifest current at revision {REVISION} ({frozen} frozen entries)")
    return 0


def _all_entries(manifest: dict):
    """Yield every artefact entry across common and per-module sections."""
    yield from manifest.get("common", [])
    for module in manifest.get("modules", {}).values():
        yield from module.get("artefacts", [])
        yield from module.get("fixtures", [])


def _report_differences(actual: dict, expected: dict) -> None:
    """Print which specific contract hashes moved, so the failure is actionable."""
    actual_hashes = {entry["path"]: entry["sha256"] for entry in _all_entries(actual)}
    expected_hashes = {entry["path"]: entry["sha256"] for entry in _all_entries(expected)}

    for path in sorted(set(expected_hashes) - set(actual_hashes)):
        print(f"      + new contract file not in manifest: {path}", file=sys.stderr)
    for path in sorted(set(actual_hashes) - set(expected_hashes)):
        print(f"      - contract file removed: {path}", file=sys.stderr)
    for path in sorted(set(actual_hashes) & set(expected_hashes)):
        if actual_hashes[path] != expected_hashes[path]:
            print(f"      ~ content changed: {path}", file=sys.stderr)
            print(
                f"          manifest: {actual_hashes[path][:16]}...\n"
                f"          on disk:  {expected_hashes[path][:16]}...",
                file=sys.stderr,
            )
    if actual.get("revision") != expected.get("revision"):
        print(
            f"      ~ revision: manifest {actual.get('revision')!r} "
            f"vs script {expected.get('revision')!r}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    raise SystemExit(main())
