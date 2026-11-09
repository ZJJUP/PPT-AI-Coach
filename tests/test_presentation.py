from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Inches

from ppt_ai_coach.demo import create_demo
from ppt_ai_coach.errors import CoachError
from ppt_ai_coach.presentation import load_presentation


def test_demo_extracts_titles_body_tables_notes(tmp_path):
    slides = load_presentation(create_demo(tmp_path / "fictional.pptx"))
    assert len(slides) == 3
    assert slides[0].number == 1
    assert slides[0].title.startswith("OrbitDesk")
    assert len(slides[0].body) == 1
    assert "scattered tasks" in slides[0].body[0]
    assert "Introduce the fictional product" in slides[0].notes
    assert slides[2].tables[0][1] == ["Pilot", "Free for two weeks"]
    assert "Table 1:" in slides[2].text()


def test_grouped_text_and_untitled_slide(tmp_path):
    ppt = Presentation()
    slide = ppt.slides.add_slide(ppt.slide_layouts[6])
    group = slide.shapes.add_group_shape()
    group.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)).text = "Grouped text"
    path = tmp_path / "groups.pptx"
    ppt.save(path)
    result = load_presentation(path)[0]
    assert result.title == "Untitled slide 1"
    assert result.body == ["Grouped text"]
    assert result.notes == ""


@pytest.mark.parametrize("name", ["missing.pptx", "legacy.ppt", "broken.pptx"])
def test_parse_failures_are_actionable(tmp_path, name):
    path = tmp_path / name
    if name != "missing.pptx":
        path.write_bytes(b"not a presentation")
    with pytest.raises(CoachError):
        load_presentation(path)


def test_empty_deck(tmp_path):
    path = Path(tmp_path) / "empty.pptx"
    Presentation().save(path)
    with pytest.raises(CoachError, match="1–500"):
        load_presentation(path)
