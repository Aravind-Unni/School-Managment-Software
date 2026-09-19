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

#: Revision and freeze state live in data, not in this script. Which modules are
#: approved is a human review outcome; hardcoding it here meant the generator
#: could only ever express "M00 is frozen", and a reviewer had to edit code to
#: record a decision.
REVISION_PATH = REPO_ROOT / "contracts" / "revision.json"

#: Contract artefact filenames, by glob, searched recursively under a module
#: directory. Recursive on purpose: the earlier top-level-only scan silently
#: omitted every schema kept in a schemas/ subdirectory -- including M02's
#: 3,549-line DTO schema -- so those files could change without the drift guard
#: ever noticing. Anything matching these globs is a contract.
ARTEFACT_GLOBS = ("openapi*.yaml", "openapi*.json", "*.schema.json", "error-codes.json")

#: Fixtures are consumer-facing examples rather than the contract itself, so they
#: are recorded in their own section. Also recursive.
FIXTURE_GLOB = "*.json"

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


def load_revision() -> dict:
    """Read the reviewed revision record from contracts/revision.json.

    Assumes the file exists and names a revision; it is part of the repository,
    not generated. Does not handle deciding whether a module *should* be frozen:
    that is a human review gate, and this file records its outcome.
    """
    if not REVISION_PATH.exists():
        raise SystemExit(
            f"FAIL: {relative(REVISION_PATH)} is missing. The manifest cannot be "
            "generated without a reviewed revision record."
        )
    revision_record = json.loads(REVISION_PATH.read_text())
    if not revision_record.get("revision"):
        raise SystemExit(f"FAIL: {relative(REVISION_PATH)} names no revision.")
    return revision_record


def artefact_paths(module_dir: pathlib.Path) -> list[pathlib.Path]:
    """Return every contract artefact under a module directory, recursively.

    Excludes anything under fixtures/, which is recorded separately. Deduplicates
    because the globs can overlap. Sorted so the manifest is byte-stable.

    Does not handle: a contract stored under a name none of ARTEFACT_GLOBS match.
    Such a file is invisible to the drift guard, so contracts must use these names.
    """
    found: set[pathlib.Path] = set()
    for pattern in ARTEFACT_GLOBS:
        for path in module_dir.rglob(pattern):
            if "fixtures" in path.relative_to(module_dir).parts:
                continue
            found.add(path)
    return sorted(found)


def build_manifest() -> dict:
    """Assemble the manifest from what is actually on disk.

    Deliberately derives entries from the filesystem instead of a hand-kept
    list, so a new schema file cannot be silently omitted from the manifest.

    Does not handle: deciding whether a contract *should* be frozen. That is a
    human review gate; contracts/revision.json records its outcome.
    """
    revision_record = load_revision()
    frozen_modules = revision_record.get("frozen_modules", {})

    common_dir = REPO_ROOT / "contracts" / "common"
    common_entries = []
    for path in sorted(common_dir.rglob("*.schema.json")):
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
        is_frozen = module_id in frozen_modules

        artefacts = []
        for path in artefact_paths(module_dir):
            artefacts.append(
                {
                    "id": f"{module_id}/{relative(path).split(module_id + '/', 1)[1]}",
                    "path": relative(path),
                    "sha256": sha256_of(path),
                    "owner": f"{module_id} {slug}",
                    "kind": "openapi" if path.name.startswith("openapi") else "json-schema",
                    "frozen": is_frozen,
                }
            )

        fixtures = []
        for path in sorted((module_dir / "fixtures").rglob(FIXTURE_GLOB)):
            fixtures.append(
                {
                    "id": f"{module_id}/fixtures/{path.name}",
                    "path": relative(path),
                    "sha256": sha256_of(path),
                    "owner": f"{module_id} {slug}",
                    "kind": "consumer-fixture",
                    "frozen": is_frozen,
                }
            )

        packet = module_dir / "PACKET.md"
        entry = {
            "slug": slug,
            "status": "frozen" if is_frozen else "not_started",
            "packet": relative(packet) if packet.exists() else None,
            "artefacts": artefacts,
            "fixtures": fixtures,
        }
        if is_frozen:
            entry["review"] = frozen_modules[module_id]
        modules[module_id] = entry

    return {
        "revision": revision_record["revision"],
        "status": revision_record.get("status", "draft"),
        "note": revision_record.get("note", ""),
        "envelope_versions": revision_record.get("envelope_versions", {"event_envelope": 1}),
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

    manifest = build_manifest()
    expected = render(manifest)
    revision = manifest["revision"]

    if arguments.update:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(expected)
        print(f"wrote {relative(MANIFEST_PATH)} at revision {revision}")
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
    print(f"OK: manifest current at revision {revision} ({frozen} frozen entries)")
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
