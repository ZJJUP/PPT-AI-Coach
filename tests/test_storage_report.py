import json

import pytest

from ppt_ai_coach.errors import CoachError
from ppt_ai_coach.report import export_report, render_report
from ppt_ai_coach.storage import HistoryStore, atomic_json


def test_history_roundtrip_is_private_and_utf8(session, tmp_path):
    session.slides[0].notes = "虚构演示备注"
    store = HistoryStore(tmp_path)
    path = store.save(session)
    restored = store.load(path)
    assert restored == session
    assert "虚构演示备注" in path.read_text(encoding="utf-8")
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("content", ["broken", "[]", '{"schema_version": 999}'])
def test_bad_history_is_recoverable(tmp_path, content):
    path = tmp_path / "history.json"
    path.write_text(content)
    with pytest.raises(CoachError):
        HistoryStore(tmp_path).load(path)


def test_path_traversal_and_invalid_turns_rejected(session, tmp_path):
    store = HistoryStore(tmp_path)
    session.id = "../outside"
    with pytest.raises(CoachError):
        store.save(session)
    data = session.to_dict()
    data["id"] = "a" * 32
    data["turns"][0]["slide_number"] = 99
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(CoachError):
        store.load(path)


def test_atomic_failure_preserves_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    atomic_json(path, {"old": True})
    monkeypatch.setattr(
        "ppt_ai_coach.storage.os.replace",
        lambda *_: (_ for _ in ()).throw(PermissionError("denied")),
    )
    with pytest.raises(PermissionError):
        atomic_json(path, {"new": True})
    assert json.loads(path.read_text()) == {"old": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_report_includes_each_page_and_honest_fallback(session, tmp_path):
    report = render_report(session)
    assert "Slide 1: OrbitDesk" in report and "Slide 2: Pilot" in report
    assert "Not practiced" in report
    assert "AI overall summary unavailable" in report
    assert session.turns[0].reply.question in report
    session.overall = "## Improve\nUse a concrete example."
    path = tmp_path / "report.md"
    export_report(session, path)
    assert session.overall in path.read_text(encoding="utf-8")


def test_export_failure_is_actionable(session, tmp_path):
    with pytest.raises(CoachError, match="报告保存失败"):
        export_report(session, tmp_path / "missing" / "report.md")
