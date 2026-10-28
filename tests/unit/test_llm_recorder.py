"""Unit tests for the LLM recorder and deterministic playback harness."""

from pathlib import Path

import pytest

from patchproof.llm.recorder import LLMRecorder


def test_recorder_record_and_playback(tmp_path: Path) -> None:
    recording_dir = tmp_path / "fixtures" / "recordings"

    # 1. Record mode
    recorder_rec = LLMRecorder(recording_dir, mode="record")
    resp1 = recorder_rec.query("Analyze root cause of bug #42", model="claude-3-7-sonnet")
    assert "[RECORDED RESPONSE FOR claude-3-7-sonnet]" in resp1

    # Verify recording file created
    rec_file = recording_dir / "llm_recordings.json"
    assert rec_file.exists()

    # 2. Playback mode
    recorder_play = LLMRecorder(recording_dir, mode="playback")
    resp2 = recorder_play.query("Analyze root cause of bug #42", model="claude-3-7-sonnet")
    assert resp2 == resp1

    # 3. Unrecorded prompt in playback mode raises KeyError
    with pytest.raises(KeyError, match="No playback recording found"):
        recorder_play.query("Unseen prompt that was never recorded", model="claude-3-7-sonnet")
