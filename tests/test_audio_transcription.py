import sys
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import soundfile as sf

from ppt_ai_coach.audio import Recorder
from ppt_ai_coach.errors import CoachError
from ppt_ai_coach.transcription import Transcriber


@pytest.fixture
def audio_device(monkeypatch):
    stream = Mock()
    sd = SimpleNamespace(
        query_devices=Mock(return_value={"default_samplerate": 48000}),
        InputStream=Mock(return_value=stream),
    )
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    return sd, stream


def test_recording_native_rate_and_duration_limit(tmp_path, audio_device):
    sd, stream = audio_device
    recorder = Recorder(max_seconds=1)
    recorder.start(device=3)
    assert sd.InputStream.call_args.kwargs["samplerate"] == 48000
    assert sd.InputStream.call_args.kwargs["device"] == 3
    recorder._callback(np.ones((60000, 1), dtype="float32") * 0.2, 60000, None, None)
    assert recorder.limit_reached.is_set()
    path = tmp_path / "speech.wav"
    recorder.stop_to_file(path)
    data, sample_rate = sf.read(path)
    assert sample_rate == 48000 and len(data) == 48000
    assert not recorder._chunks
    stream.close.assert_called()


def test_silence_and_microphone_failure(tmp_path, audio_device):
    sd, _ = audio_device
    recorder = Recorder()
    recorder.start()
    recorder._callback(np.zeros((24000, 1), dtype="float32"), 24000, None, None)
    with pytest.raises(CoachError, match="无声"):
        recorder.stop_to_file(tmp_path / "silent.wav")
    sd.InputStream.side_effect = OSError("device unavailable")
    with pytest.raises(CoachError, match="麦克风启动失败"):
        recorder.start()


def test_transcriber_cpu_int8_and_offline(tmp_path, monkeypatch):
    model = Mock()
    model.transcribe.return_value = (
        iter([SimpleNamespace(text=" Hello "), SimpleNamespace(text=" world. ")]),
        None,
    )
    factory = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=factory))
    monkeypatch.setenv("PPT_AI_COACH_DATA_DIR", str(tmp_path))
    transcriber = Transcriber("tiny.en", offline=True)
    assert transcriber.transcribe(tmp_path / "input.wav") == "Hello world."
    transcriber.load()
    assert factory.call_count == 1
    assert factory.call_args.kwargs["compute_type"] == "int8"
    assert factory.call_args.kwargs["device"] == "cpu"
    assert factory.call_args.kwargs["local_files_only"] is True
    assert model.transcribe.call_args.kwargs["language"] == "en"


def test_transcriber_model_failure_and_empty_audio(tmp_path, monkeypatch):
    factory = Mock(side_effect=OSError("offline"))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=factory))
    with pytest.raises(CoachError, match="模型加载失败"):
        Transcriber().load()
    model = Mock()
    model.transcribe.return_value = (iter([]), None)
    factory.side_effect, factory.return_value = None, model
    with pytest.raises(CoachError, match="未识别"):
        Transcriber().transcribe(tmp_path / "silent.wav")
