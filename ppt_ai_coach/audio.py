import threading
from pathlib import Path

from .errors import CoachError


def input_devices() -> list[tuple[int, str]]:
    try:
        import sounddevice as sd

        return [
            (index, device["name"])
            for index, device in enumerate(sd.query_devices())
            if device["max_input_channels"] > 0
        ]
    except Exception as exc:
        raise CoachError("无法读取麦克风设备。请检查音频驱动和 Windows 麦克风权限。") from exc


class Recorder:
    def __init__(self, max_seconds: int = 300):
        self.max_seconds = max_seconds
        self.sample_rate = 16000
        self._stream = None
        self._chunks = []
        self._frames = 0
        self._lock = threading.Lock()
        self.limit_reached = threading.Event()
        self._problem = ""

    def start(self, device: int | None = None) -> None:
        import sounddevice as sd

        if self._stream is not None:
            raise CoachError("录音已经开始。")
        self._chunks, self._frames, self._problem = [], 0, ""
        self.limit_reached.clear()
        try:
            # Many Windows devices support only 44.1/48 kHz. Use their native rate;
            # Whisper's audio decoder resamples the resulting WAV to 16 kHz.
            self.sample_rate = int(sd.query_devices(device, "input")["default_samplerate"])
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=device,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:
            self.abort()
            raise CoachError(
                "麦克风启动失败。请允许桌面应用访问麦克风、选择正确设备，并关闭独占音频的程序。"
            ) from exc

    def _callback(self, data, frames, time_info, status):
        if status:
            self._problem = "录音发生缓冲溢出或设备异常，请关闭高负载程序后重录。"
        with self._lock:
            remaining = self.max_seconds * self.sample_rate - self._frames
            if remaining > 0:
                chunk = data[:remaining].copy()
                self._chunks.append(chunk)
                self._frames += len(chunk)
            if self._frames >= self.max_seconds * self.sample_rate:
                self.limit_reached.set()

    def abort(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
            finally:
                stream.close()
        with self._lock:
            self._chunks = []

    def stop_to_file(self, path: Path) -> None:
        import numpy as np
        import soundfile as sf

        stream, self._stream = self._stream, None
        if stream is None:
            raise CoachError("当前没有录音。")
        try:
            stream.stop()
            stream.close()
            with self._lock:
                chunks, self._chunks = self._chunks, []
            if self._problem:
                raise CoachError(self._problem)
            if not chunks:
                raise CoachError("未录到声音，请检查麦克风。")
            audio = np.concatenate(chunks, axis=0)
            if len(audio) < self.sample_rate // 2 or float(np.max(np.abs(audio))) < 0.001:
                raise CoachError("录音过短或基本无声，请检查设备后重录。")
            sf.write(str(path), audio, self.sample_rate, subtype="PCM_16")
        except CoachError:
            raise
        except Exception as exc:
            raise CoachError("录音保存失败，请检查设备连接及临时目录权限。") from exc
        finally:
            # close is idempotent for sounddevice streams.
            stream.close()
