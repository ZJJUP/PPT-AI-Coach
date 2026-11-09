from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Slide:
    number: int
    title: str
    body: list[str] = field(default_factory=list)
    tables: list[list[list[str]]] = field(default_factory=list)
    notes: str = ""

    def text(self) -> str:
        parts = [f"Slide {self.number}: {self.title}", *self.body]
        for index, table in enumerate(self.tables, 1):
            parts.append(f"Table {index}:")
            parts.extend(" | ".join(row) for row in table)
        if self.notes:
            parts.append(f"Speaker notes:\n{self.notes}")
        return "\n".join(parts)


@dataclass
class Reply:
    feedback: str
    improved_example: str
    question: str

    def text(self) -> str:
        return (
            f"Feedback: {self.feedback}\n\n"
            f"Try saying: {self.improved_example}\n\n"
            f"Customer question: {self.question}"
        )


@dataclass
class Turn:
    slide_number: int
    mode: str
    transcript: str
    reply: Reply
    created_at: str = field(default_factory=now)


@dataclass
class Session:
    deck_name: str
    slides: list[Slide]
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=now)
    turns: list[Turn] = field(default_factory=list)
    overall: str = ""

    def to_dict(self) -> dict:
        return {"schema_version": 1, **asdict(self)}

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported session version")
        slides = [Slide(**item) for item in data["slides"]]
        turns = [Turn(**{**item, "reply": Reply(**item["reply"])}) for item in data["turns"]]
        if not slides or len(slides) > 500 or len(turns) > 10000:
            raise ValueError("Invalid session size")
        numbers = {slide.number for slide in slides}
        if numbers != set(range(1, len(slides) + 1)):
            raise ValueError("Invalid slide numbers")
        if any(
            t.slide_number not in numbers or t.mode not in {"presentation", "discussion"}
            for t in turns
        ):
            raise ValueError("Invalid turn")
        for slide in slides:
            if not isinstance(slide.title, str) or not isinstance(slide.notes, str):
                raise ValueError("Invalid slide text")
            if not isinstance(slide.body, list) or any(not isinstance(x, str) for x in slide.body):
                raise ValueError("Invalid slide body")
            if not isinstance(slide.tables, list) or any(
                not isinstance(table, list)
                or any(
                    not isinstance(row, list) or any(not isinstance(cell, str) for cell in row)
                    for row in table
                )
                for table in slide.tables
            ):
                raise ValueError("Invalid slide tables")
        for turn in turns:
            if not all(
                isinstance(x, str)
                for x in (
                    turn.transcript,
                    turn.created_at,
                    turn.reply.feedback,
                    turn.reply.improved_example,
                    turn.reply.question,
                )
            ):
                raise ValueError("Invalid turn text")
        if not all(
            isinstance(data.get(x), str) for x in ("id", "created_at", "deck_name", "overall")
        ):
            raise ValueError("Invalid session metadata")
        return cls(
            deck_name=data["deck_name"],
            slides=slides,
            id=data["id"],
            created_at=data["created_at"],
            turns=turns,
            overall=data["overall"],
        )
