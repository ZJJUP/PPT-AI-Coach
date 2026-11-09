from pathlib import Path
from zipfile import ZipFile

from .errors import CoachError
from .models import Slide


def _walk(shapes):
    for shape in shapes:
        yield shape
        if hasattr(shape, "shapes"):
            yield from _walk(shape.shapes)


def load_presentation(path: Path) -> list[Slide]:
    """Read text, tables and available notes; never execute embedded content."""
    from pptx import Presentation

    path = Path(path)
    if path.suffix.lower() != ".pptx":
        raise CoachError("仅支持 .pptx。请先用 PowerPoint 将 .ppt/.pptm 另存为 .pptx。")
    try:
        if path.stat().st_size > 100 * 1024 * 1024:
            raise CoachError("PPTX 超过 100 MB，请先压缩图片或拆分文件。")
        with ZipFile(path) as archive:
            if sum(item.file_size for item in archive.infolist()) > 512 * 1024 * 1024:
                raise CoachError("PPTX 解压内容过大，请拆分文件后重试。")
        ppt = Presentation(str(path))
        if not 1 <= len(ppt.slides) <= 500:
            raise CoachError("PPTX 需要包含 1–500 页。")
        result = []
        for number, source in enumerate(ppt.slides, 1):
            title_shape = source.shapes.title
            title = title_shape.text.strip() if title_shape is not None else ""
            body, tables = [], []
            for shape in _walk(source.shapes):
                if title_shape is not None and shape.shape_id == title_shape.shape_id:
                    continue
                if shape.has_table:
                    tables.append(
                        [[cell.text.strip() for cell in row.cells] for row in shape.table.rows]
                    )
                elif shape.has_text_frame and shape.text.strip():
                    body.append(shape.text.strip())
            notes = ""
            if source.has_notes_slide:
                frame = source.notes_slide.notes_text_frame
                if frame is not None:
                    notes = frame.text.strip()
            result.append(Slide(number, title or f"Untitled slide {number}", body, tables, notes))
        return result
    except CoachError:
        raise
    except Exception as exc:
        # python-pptx/lxml expose several parser-specific exception classes.
        raise CoachError(
            "PPTX 读取失败：文件可能损坏、被加密或不可访问。请另存为新 PPTX。"
        ) from exc
