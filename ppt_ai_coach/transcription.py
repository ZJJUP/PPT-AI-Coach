from pathlib import Path

from .errors import CoachError
from .storage import data_dir

MODEL_NAMES = ("tiny.en", "base.en", "small.en", "medium.en")


class Transcriber:
    def __init__(self, model: str = "base.en", offline: bool = False):
        self.model_name = model
        self.offline = offline
        self._model = None

    def load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                    download_root=str(data_dir() / "models"),
                    local_files_only=self.offline,
                    cpu_threads=4,
                )
            except Exception as exc:
                raise CoachError(
                    "Whisper 模型加载失败。首次使用需联网下载；请运行 tools/download_model.py。"
                    "离线模式需提前缓存模型；低内存电脑请选择 tiny.en。"
                ) from exc
        return self._model

    def transcribe(self, path: Path) -> str:
        try:
            segments, _ = self.load().transcribe(
                str(path),
                language="en",
                beam_size=5,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            if not text:
                raise CoachError("未识别到英语语音，请靠近麦克风重试，或直接在文本框输入。")
            return text
        except CoachError:
            raise
        except Exception as exc:
            raise CoachError("语音转写失败。请检查音频、模型和可用内存，或改用文本输入。") from exc
