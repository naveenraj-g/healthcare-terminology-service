#!/bin/sh
# Runs all terminology imports in the correct order (mirrors terminology-all in justfile).
# All steps are idempotent — safe to re-run.
# Expects terminology_data/ to be mounted at /terminology_data inside the container.
set -e

DATA=/terminology_data

echo "=== Terminology seeding started ==="

echo "[1/8] FHIR R4 — v3-codesystems..."
uv run python -m app.terminology.import_.cli --source fhir-r4 --file "$DATA/v3-codesystems.json"

echo "[2/8] FHIR R4 — v2-tables..."
uv run python -m app.terminology.import_.cli --source fhir-r4 --file "$DATA/v2-tables.json"

echo "[3/8] FHIR R4 — valuesets..."
uv run python -m app.terminology.import_.cli --source fhir-r4 --file "$DATA/valuesets.json"

echo "[4/8] ICD-10-CM..."
uv run python -m app.terminology.import_.cli --source icd10cm --file "$DATA/icd10cm_codes_2026.txt"

echo "[5/8] RxNorm..."
uv run python -m app.terminology.import_.cli --source rxnorm --file "$DATA/rrf/RXNCONSO.RRF"

echo "[6/8] LOINC..."
uv run python -m app.terminology.import_.cli --source loinc --file "$DATA/LoincTableCore.csv"

echo "[7/8] SNOMED CT..."
uv run python -m app.terminology.import_.cli --source snomed --dir "$DATA/SnomedCT_USEdition/Snapshot/Terminology"

echo "[8/8] FHIR R4 field bindings..."
uv run python -m app.terminology.seed_field_bindings_r4

echo "=== Terminology seeding complete ==="
