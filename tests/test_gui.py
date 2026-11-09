import gc
import os
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import Mock

import pytest

from ppt_ai_coach.errors import CoachError
from ppt_ai_coach.gui import CoachApp
from ppt_ai_coach.models import Reply

pytestmark = pytest.mark.gui


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Tk objects from prior roots must be collected on the main thread.
    gc.collect()
    if os.name != "nt" and not os.environ.get("DISPLAY"):
        pytest.skip("GUI tests require X11 (e.g. xvfb-run) or Windows desktop")
    monkeypatch.setenv("PPT_AI_COACH_DATA_DIR", str(tmp_path))
    root = tk.Tk()
    root.withdraw()
    result = CoachApp(root)
    result.voice_mode.set("off")
    monkeypatch.setattr("ppt_ai_coach.gui.messagebox.showinfo", Mock())
    monkeypatch.setattr("ppt_ai_coach.gui.messagebox.showerror", Mock())
    yield result
    result.closed = True
    root.after_cancel(result._poll_id)
    result.speech.stop()
    root.destroy()


def wait_idle(app):
    deadline = time.monotonic() + 5
    while app.state != "idle":
        app.root.update()
        if time.monotonic() > deadline:
            pytest.fail("Background work did not finish")
        time.sleep(0.01)


def test_demo_navigation_keeps_per_slide_drafts(app):
    app.open_demo()
    wait_idle(app)
    assert len(app.session.slides) == 3
    assert "OrbitDesk" in app.slide_text.get("1.0", "end")
    app.transcript.insert("1.0", "Draft for slide one")
    app.navigate(1)
    assert not app.transcript.get("1.0", "end").strip()
    app.transcript.insert("1.0", "Draft for slide two")
    app.navigate(-1)
    assert app.transcript.get("1.0", "end").strip() == "Draft for slide one"


def test_text_conversation_history_and_report(app, monkeypatch, tmp_path):
    app.open_demo()
    wait_idle(app)
    reply = Reply("Give one example.", "We bring plans into one place.", "Who would join a pilot?")
    client = Mock()
    client.coach.return_value = reply
    client.summarize.return_value = "## Next steps\nExplain the pilot clearly."
    monkeypatch.setattr(app, "_client", lambda: client)
    app.transcript.insert("1.0", "We help small teams.")
    app.send()
    wait_idle(app)
    assert len(app.session.turns) == 1
    assert "Who would join" in app.conversation.get("1.0", "end")
    assert not app.transcript.get("1.0", "end").strip()
    assert app.history.load(next(app.history.root.glob("*.json"))) == app.session
    app.mode.set("discussion")
    app.transcript.insert("1.0", "A volunteer design team could try it.")
    app.send()
    wait_idle(app)
    assert app.session.turns[-1].mode == "discussion"
    assert len(client.coach.call_args.args[2]) == 2
    path = tmp_path / "report.md"
    monkeypatch.setattr("ppt_ai_coach.gui.filedialog.asksaveasfilename", lambda **_: str(path))
    app.export()
    wait_idle(app)
    assert "Explain the pilot clearly" in path.read_text()
    assert "Slide 3" in path.read_text()


def test_api_failure_preserves_retry_text(app, monkeypatch):
    app.open_demo()
    wait_idle(app)
    client = Mock()
    client.coach.side_effect = CoachError("Codex 调用超时")
    monkeypatch.setattr(app, "_client", lambda: client)
    app.transcript.insert("1.0", "Keep this text for retry.")
    app.send()
    wait_idle(app)
    assert app.transcript.get("1.0", "end").strip() == "Keep this text for retry."
    assert not app.session.turns


def test_speech_notice_does_not_unlock_recording(app):
    app._set_state("recording")
    app.events.put(("speech", "TTS failed", None))
    app._poll()
    assert app.state == "recording"
    assert str(app.stop_button["state"]) == "normal"


def test_microphone_transcription_flow_deletes_audio(app, monkeypatch):
    app.open_demo()
    wait_idle(app)
    recorder = Mock()
    recorder.limit_reached.is_set.return_value = False
    recorder.stop_to_file.side_effect = lambda path: path.write_bytes(b"mock audio")
    app.recorder = recorder
    transcriber = Mock()
    transcriber.model_name, transcriber.offline = "base.en", False
    transcriber.transcribe.return_value = "Hello from a fictional pilot."
    app.transcriber = transcriber
    app.start_recording()
    deadline = time.monotonic() + 5
    while app.state != "recording":
        app.root.update()
        assert time.monotonic() < deadline
        time.sleep(0.01)
    app.stop_recording()
    wait_idle(app)
    assert "Hello from a fictional pilot" in app.transcript.get("1.0", "end")
    path = transcriber.transcribe.call_args.args[0]
    assert isinstance(path, Path) and not path.exists()
