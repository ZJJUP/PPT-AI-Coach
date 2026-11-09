import pytest

from ppt_ai_coach.models import Reply, Session, Slide, Turn


@pytest.fixture
def session():
    slides = [
        Slide(1, "OrbitDesk", ["A fictional planning app"], notes="Ask about goals"),
        Slide(2, "Pilot", ["Two weeks"]),
    ]
    result = Session("fictional-demo.pptx", slides)
    result.turns.append(
        Turn(
            1,
            "presentation",
            "We help teams plan their week.",
            Reply(
                "Explain the benefit with an example.",
                "Our app gives teams one shared weekly plan.",
                "How would a team start a pilot?",
            ),
        )
    )
    return result
