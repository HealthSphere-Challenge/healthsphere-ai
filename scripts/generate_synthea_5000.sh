#!/usr/bin/env bash
set -euo pipefail

readonly VERSION="4.0.0"
readonly POPULATION="5000"
readonly SEED="20260913"
readonly CLINICIAN_SEED="20260914"
readonly REFERENCE_DATE="20260913"
readonly GEOGRAPHY="Massachusetts"
readonly ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly CACHE_DIR="${ROOT}/.cache/synthea/${VERSION}"
readonly OUTPUT_DIR="${ROOT}/data/raw/synthea_5000_reproducible"
readonly JAR="${CACHE_DIR}/synthea-with-dependencies.jar"
readonly URL="https://github.com/synthetichealth/synthea/releases/download/v${VERSION}/synthea-with-dependencies.jar"

mkdir -p "${CACHE_DIR}" "${OUTPUT_DIR}"
if [[ ! -f "${JAR}" ]]; then
  curl --fail --location --output "${JAR}" "${URL}"
fi

java -jar "${JAR}" \
  -s "${SEED}" -cs "${CLINICIAN_SEED}" -r "${REFERENCE_DATE}" -e "${REFERENCE_DATE}" \
  -p "${POPULATION}" \
  --exporter.baseDirectory="${OUTPUT_DIR}" \
  --exporter.csv.export=true \
  --exporter.fhir.export=false \
  --exporter.ccda.export=false \
  --exporter.text.export=false \
  "${GEOGRAPHY}"
