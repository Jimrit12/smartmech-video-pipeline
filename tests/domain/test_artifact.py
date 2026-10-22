"""Tests for artifact key calculation and canonical hashing."""

from pydantic import BaseModel

from smartmech.domain.artifact import (
    ProvenanceManifest,
    compute_artifact_key,
    compute_canonical_input_hash,
)


class DummyModel(BaseModel):
    name: str
    val: int


def test_compute_canonical_input_hash() -> None:
    # BaseModel
    h1 = compute_canonical_input_hash(DummyModel(name="test", val=42))
    assert len(h1) == 64

    # Dict and List
    h2 = compute_canonical_input_hash({"b": 2, "a": 1})
    h3 = compute_canonical_input_hash([1, 2, 3])
    assert len(h2) == 64
    assert len(h3) == 64

    # Bytes and String
    h4 = compute_canonical_input_hash(b"raw_bytes")
    h5 = compute_canonical_input_hash("string_value")
    assert len(h4) == 64
    assert len(h5) == 64


def test_compute_artifact_key_deterministic() -> None:
    k1 = compute_artifact_key("image_gen", "fake", "v1", "prompt_text", 42)
    k2 = compute_artifact_key("image_gen", "fake", "v1", "prompt_text", 42)
    k3 = compute_artifact_key("image_gen", "fake", "v1", "prompt_text", 43)

    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 64


def test_provenance_manifest_creation() -> None:
    manifest = ProvenanceManifest(
        artifact_key="a" * 64,
        run_id="run-1",
        port="image_gen",
        adapter="fake",
        model_or_version="v1",
        seed=1,
        cost_units=0.5,
        file_extension="png",
    )
    assert manifest.artifact_key == "a" * 64


def test_clip_key_depends_on_parent_keyframes_and_invalidates() -> None:
    kf0_key = "0" * 64
    kf1_key = "1" * 64
    kf1_alt_key = "2" * 64

    # Baseline clip key with kf0 and kf1
    clip_key1 = compute_artifact_key(
        port="video_gen",
        adapter="vendor_x",
        model_or_version="gen-2",
        canonical_input="Smooth crane rise",
        seed=10,
        input_artifact_keys=[kf0_key, kf1_key],
    )
    # Identical inputs produce identical key (cache hit)
    clip_key2 = compute_artifact_key(
        port="video_gen",
        adapter="vendor_x",
        model_or_version="gen-2",
        canonical_input="Smooth crane rise",
        seed=10,
        input_artifact_keys=[kf0_key, kf1_key],
    )
    assert clip_key1 == clip_key2

    # Changing a keyframe invalidates the clip key
    clip_key_invalidated = compute_artifact_key(
        port="video_gen",
        adapter="vendor_x",
        model_or_version="gen-2",
        canonical_input="Smooth crane rise",
        seed=10,
        input_artifact_keys=[kf0_key, kf1_alt_key],
    )
    assert clip_key_invalidated != clip_key1

    # Key depends on adapter identity: changing model/version invalidates key
    clip_key_new_model = compute_artifact_key(
        port="video_gen",
        adapter="vendor_x",
        model_or_version="gen-3",
        canonical_input="Smooth crane rise",
        seed=10,
        input_artifact_keys=[kf0_key, kf1_key],
    )
    assert clip_key_new_model != clip_key1
