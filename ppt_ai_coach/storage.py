import json
import os
import re
import tempfile
from pathlib import Path

from .errors import CoachError
from .models import Session


def data_dir() -> Path:
    override = os.environ.get("PPT_AI_COACH_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "PPT-AI-Coach"


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)


class HistoryStore:
    def __init__(self, root: Path | None = None):
        self.root = root if root is not None else data_dir() / "sessions"

    def save(self, session: Session) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}", session.id):
            raise CoachError("历史记录 ID 无效。")
        path = self.root / f"{session.id}.json"
        try:
            atomic_json(path, session.to_dict())
            return path
        except OSError as exc:
            raise CoachError("无法保存历史记录，请检查用户数据目录权限和磁盘空间。") from exc

    def load(self, path: Path) -> Session:
        try:
            if path.stat().st_size > 30 * 1024 * 1024:
                raise ValueError("Session too large")
            session = Session.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if not re.fullmatch(r"[a-f0-9]{32}", session.id):
                raise ValueError("Invalid session ID")
            return session
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise CoachError("历史记录损坏或版本不兼容，请选择其他 JSON 文件。") from exc
