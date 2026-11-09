from unittest.mock import Mock

from ppt_ai_coach.speech import SpeechService


def test_edge_failure_falls_back_to_local(monkeypatch):
    speech = SpeechService()
    monkeypatch.setattr(speech, "_edge", Mock(side_effect=OSError("offline")))
    local = Mock()
    monkeypatch.setattr(speech, "_local", local)
    assert "本地" in speech.speak("How would you start?")
    local.assert_called_once()


def test_off_and_cancelled_requests_never_play(monkeypatch):
    speech = SpeechService()
    edge, local = Mock(), Mock()
    monkeypatch.setattr(speech, "_edge", edge)
    monkeypatch.setattr(speech, "_local", local)
    speech.speak("Hello", mode="off")
    old = speech.new_request()
    latest = speech.new_request()
    assert old.is_set()
    speech.speak("old", cancel=old)
    edge.assert_not_called()
    speech.speak("new", mode="local", cancel=latest)
    local.assert_called_once_with("new", latest)
