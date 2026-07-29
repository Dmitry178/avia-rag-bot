"""Tests for ingest checkpoint temp-file cleanup."""

from app.services.etl_checkpoint import (
    IngestCheckpointStore,
    checkpoint_artifact_paths,
    cleanup_ingest_temp_files,
)


def test_checkpoint_store_clear_removes_json_and_tmp(tmp_path) -> None:
    """
    clear() should delete both the checkpoint JSON and its .tmp sibling.
    """

    json_path, temp_path = checkpoint_artifact_paths(tmp_path, "en")
    json_path.write_text("{}", encoding="utf-8")
    temp_path.write_text("{}", encoding="utf-8")

    IngestCheckpointStore(json_path).clear()

    assert not json_path.is_file()
    assert not temp_path.is_file()


def test_cleanup_ingest_temp_files_removes_language_artifacts(tmp_path) -> None:
    """
    Post-ingest cleanup should remove checkpoint files for completed languages only.
    """

    en_json, en_tmp = checkpoint_artifact_paths(tmp_path, "en")
    ru_json, _ = checkpoint_artifact_paths(tmp_path, "ru")
    en_json.write_text("{}", encoding="utf-8")
    en_tmp.write_text("{}", encoding="utf-8")
    ru_json.write_text("{}", encoding="utf-8")

    removed = cleanup_ingest_temp_files(tmp_path, language_codes=["en"])

    assert en_json in removed
    assert not en_json.is_file()
    assert not en_tmp.is_file()
    assert ru_json.is_file()
