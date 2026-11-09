from collections import Counter
from pathlib import Path

from .errors import CoachError
from .models import Session


def render_report(session: Session) -> str:
    counts = Counter(turn.slide_number for turn in session.turns)
    lines = [
        "# PPT-AI-Coach practice report",
        "",
        f"Presentation: {session.deck_name}",
        f"Session started (UTC): {session.created_at}",
        f"Practice turns: {len(session.turns)}; "
        f"slides practiced: {len(counts)}/{len(session.slides)}",
        "",
        "## Overall improvement plan",
        "",
        session.overall
        or (
            "AI overall summary unavailable. Review the per-slide feedback below. "
            "Practice a clear opening, support claims with evidence, and answer each customer "
            "question with a specific example. "
            "These are general practice tips, not an AI assessment."
        ),
        "",
        "This report evaluates wording, structure and customer relevance from text. "
        "It does not score pronunciation, timing, or factual accuracy.",
        "",
    ]
    for slide in session.slides:
        lines.extend([f"## Slide {slide.number}: {slide.title}", ""])
        turns = [turn for turn in session.turns if turn.slide_number == slide.number]
        if not turns:
            lines.extend(["Not practiced in this session.", ""])
        for index, turn in enumerate(turns, 1):
            lines.extend(
                [
                    f"### Turn {index} ({turn.mode}, {turn.created_at})",
                    "",
                    "**You said**",
                    "",
                    turn.transcript,
                    "",
                    "**Coach feedback**",
                    "",
                    turn.reply.feedback,
                    "",
                    "**Suggested wording**",
                    "",
                    turn.reply.improved_example,
                    "",
                    "**Customer follow-up**",
                    "",
                    turn.reply.question,
                    "",
                ]
            )
    return "\n".join(lines)


def export_report(session: Session, path: Path) -> None:
    try:
        path.write_text(render_report(session), encoding="utf-8")
    except OSError as exc:
        raise CoachError("报告保存失败，请检查目标目录权限和磁盘空间。") from exc
