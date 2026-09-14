import json
import shutil
from pathlib import Path

import pytest

from healthsphere_ai.artifacts import ArtifactError, ModelBundle

SOURCE = Path("artifacts/hypertension_5y/v1")


def copied_artifacts(tmp_path: Path) -> Path:
    destination = tmp_path / "artifacts"
    shutil.copytree(SOURCE, destination)
    return destination


def test_frozen_bundle_loads_without_raw_synthea():
    bundle = ModelBundle.load(SOURCE)
    assert bundle.metadata["model_version"] == "hypertension_5y_v1.0.0"


@pytest.mark.parametrize(
    "filename", ["model.json", "preprocessing.joblib", "metrics.json", "split_manifest.json"]
)
def test_missing_primary_artifact_fails(tmp_path, filename):
    directory = copied_artifacts(tmp_path)
    (directory / filename).unlink()
    with pytest.raises(ArtifactError, match="missing"):
        ModelBundle.load(directory)


def test_hash_mismatch_fails(tmp_path):
    directory = copied_artifacts(tmp_path)
    with (directory / "model.json").open("a") as stream:
        stream.write("corruption")
    with pytest.raises(ArtifactError, match="integrity"):
        ModelBundle.load(directory)


def test_invalid_metadata_fails(tmp_path):
    directory = copied_artifacts(tmp_path)
    (directory / "metadata.json").write_text("not-json")
    with pytest.raises(ArtifactError, match="metadata"):
        ModelBundle.load(directory)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_id", "wrong-target"),
        ("feature_schema_version", "wrong-schema"),
        ("model_version", "wrong-model"),
        ("model_class", "wrong-class"),
    ],
)
def test_metadata_compatibility_fails_closed(tmp_path, field, value):
    directory = copied_artifacts(tmp_path)
    path = directory / "metadata.json"
    metadata = json.loads(path.read_text())
    metadata[field] = value
    path.write_text(json.dumps(metadata))
    with pytest.raises(ArtifactError, match=field):
        ModelBundle.load(directory)
