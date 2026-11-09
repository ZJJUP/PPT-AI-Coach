from pathlib import Path


def create_demo(path: Path) -> Path:
    """Generate only original, fictional product content. No third-party deck assets."""
    from pptx import Presentation
    from pptx.util import Inches

    ppt = Presentation()
    slides = [
        (
            "OrbitDesk — A calmer way to plan",
            [
                "A fictional planning app for small creative teams",
                "Turn scattered tasks into a shared weekly plan",
                "A demonstration only: no real customers or performance claims",
            ],
            "Introduce the fictional product. Ask which planning problem matters most.",
        ),
        (
            "From scattered tasks to a shared plan",
            [
                "Capture ideas in one inbox",
                "Choose three priorities for the week",
                "Review progress together in a 10-minute check-in",
            ],
            "Explain the workflow in plain English. Avoid promising measured time savings.",
        ),
        (
            "A small, low-risk pilot",
            [
                "Try the fictional product with one volunteer team",
                "Agree on success criteria before starting",
                "Discuss feedback at the end of two weeks",
            ],
            "These prices and plans are invented for speaking practice.",
        ),
    ]
    for title, bullets, notes in slides:
        slide = ppt.slides.add_slide(ppt.slide_layouts[1])
        slide.shapes.title.text = title
        frame = slide.placeholders[1].text_frame
        for index, bullet in enumerate(bullets):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.text = bullet
        slide.notes_slide.notes_text_frame.text = notes
    table = (
        ppt.slides[2]
        .shapes.add_table(3, 2, Inches(0.6), Inches(4.6), Inches(8.3), Inches(1.3))
        .table
    )
    for row, values in enumerate(
        [
            ("Fictional plan", "Illustrative price"),
            ("Pilot", "Free for two weeks"),
            ("Team", "$8 per user / month (fictional)"),
        ]
    ):
        for column, value in enumerate(values):
            table.cell(row, column).text = value
    path.parent.mkdir(parents=True, exist_ok=True)
    ppt.save(str(path))
    return path
