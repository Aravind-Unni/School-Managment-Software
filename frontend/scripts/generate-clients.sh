#!/usr/bin/env bash
# Generate typed OpenAPI clients. Skip modules whose frozen OpenAPI cannot bundle.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=../contracts
OUT=src/features

generate() {
  local id="$1"
  local src="$2"
  local dest="$3"
  echo "==> $id"
  if npx openapi-typescript "$src" -o "$dest"; then
    return 0
  fi
  echo "WARN: skipped $id (OpenAPI could not be bundled)" >&2
  return 0
}

generate M00 "$ROOT/M00/openapi.yaml" "$OUT/demo/generated/schema.d.ts"
generate M01 "$ROOT/M01/openapi.yaml" "$OUT/access/generated/schema.d.ts"
generate M02 "$ROOT/M02/openapi.json" "$OUT/registry/generated/schema.d.ts"
generate M03 "$ROOT/M03/openapi.json" "$OUT/timetable/generated/schema.d.ts"
generate M04 "$ROOT/M04/openapi.json" "$OUT/attendance/generated/schema.d.ts"
# M05 skipped — unresolved $refs in frozen packet; hand-typed api.ts remains.
echo "==> M05 (skipped: unresolved OpenAPI \$refs)"
generate M06 "$ROOT/M06/openapi.json" "$OUT/performance/generated/schema.d.ts"
generate M07 "$ROOT/M07/openapi.json" "$OUT/fees/generated/schema.d.ts"
generate M08 "$ROOT/M08/openapi.json" "$OUT/transport/generated/schema.d.ts"
generate M09 "$ROOT/M09/openapi.json" "$OUT/library/generated/schema.d.ts"
generate M10 "$ROOT/M10/openapi.json" "$OUT/alumni/generated/schema.d.ts"
generate M11 "$ROOT/M11/openapi.json" "$OUT/communications/generated/schema.d.ts"
generate M12 "$ROOT/M12/openapi.json" "$OUT/files/generated/schema.d.ts"
generate M13 "$ROOT/M13/openapi.json" "$OUT/exchange/generated/schema.d.ts"
generate M14 "$ROOT/M14/openapi.json" "$OUT/platform/generated/schema.d.ts"
echo "done"
