"""Edge speech with interruptible Windows playback and an offline SAPI fallback."""

import asyncio
import ctypes
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .errors import CoachError


class SpeechService:
    def __init__(self):
        self._cancel = threading.Event()
        self._lock = threading.Lock()

    def stop(self):
        self._cancel.set()

    def new_request(self):
        self.stop()
        self._cancel = threading.Event()
        return self._cancel

    def speak(
        self,
        text: str,
        mode: str = "auto",
        voice: str = "en-US-AriaNeural",
        cancel: threading.Event | None = None,
    ) -> str:
        if mode == "off":
            return ""
        cancel = cancel if cancel is not None else self.new_request()
        with self._lock:
            if cancel.is_set():
                return ""
            if mode == "local":
                self._local(text, cancel)
                return ""
            try:
                self._edge(text, voice, cancel)
                return ""
            except Exception:
                if cancel.is_set():
                    return ""
                self._local(text, cancel)
                return "Edge TTS 不可用，已使用 Windows 本地英语语音。"

    def _edge(self, text: str, voice: str, cancel):
        if os.name != "nt":
            raise CoachError("音频播放面向 Windows；当前系统请阅读文字反馈。")
        import edge_tts

        with tempfile.TemporaryDirectory(prefix="ppt-coach-tts-") as directory:
            path = Path(directory) / "voice.mp3"

            async def synthesize():
                await asyncio.wait_for(edge_tts.Communicate(text, voice).save(str(path)), 30)

            asyncio.run(synthesize())
            if cancel.is_set():
                return
            self._play_mp3(path, cancel)

    def _play_mp3(self, path: Path, cancel):
        winmm = ctypes.WinDLL("winmm")
        send = winmm.mciSendStringW
        send.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        send.restype = ctypes.c_uint
        alias = "pptcoachvoice"

        def command(value: str) -> str:
            buffer = ctypes.create_unicode_buffer(256)
            if send(value, buffer, len(buffer), None):
                raise CoachError("Windows MP3 播放失败。")
            return buffer.value

        try:
            command(f'open "{path}" type mpegvideo alias {alias}')
            command(f"play {alias}")
            deadline = time.monotonic() + 180
            while not cancel.wait(0.1):
                if command(f"status {alias} mode") != "playing":
                    break
                if time.monotonic() > deadline:
                    raise CoachError("语音播放超时。")
        finally:
            send(f"close {alias}", None, 0, None)

    def _local(self, text: str, cancel):
        if os.name != "nt":
            raise CoachError("Windows 本地 TTS 仅支持 Windows；文字反馈已保留。")
        executable = shutil.which("powershell.exe")
        if not executable:
            raise CoachError("找不到 Windows PowerShell，请检查系统安装。")
        script = r"""
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  $speaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,
    [System.Speech.Synthesis.VoiceAge]::NotSet, 0,
    [System.Globalization.CultureInfo]::GetCultureInfo('en-US'))
  $speaker.Speak([Console]::In.ReadToEnd())
} finally { $speaker.Dispose() }
"""
        try:
            process = subprocess.Popen(
                [executable, "-NoProfile", "-NonInteractive", "-Command", script],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                process.stdin.write(text.encode("utf-8"))
                process.stdin.close()
                deadline = time.monotonic() + 180
                while process.poll() is None:
                    if cancel.wait(0.1):
                        break
                    if time.monotonic() > deadline:
                        raise CoachError("Windows 语音超时。")
                if process.poll() not in (None, 0):
                    raise CoachError("Windows 英语语音不可用，请安装系统英语语音包。")
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
        except CoachError:
            raise
        except Exception as exc:
            raise CoachError("本地 TTS 失败，请检查 Windows 英语语音包。文字反馈已保留。") from exc
