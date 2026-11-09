# Maintaining PPT-AI-Coach

- Target Windows 10/11 x64 and Python 3.11; keep Tkinter and lazy imports for audio/Whisper.
- Keep domain logic separate from Tkinter. Workers must never call Tk widgets; use the event queue.
- Use the user's local authenticated Codex CLI through subprocess, stdin and structured output.
  Never read/copy credentials, put prompts in shell command strings, or remove read-only sandboxing.
- Never commit user PPTs, audio, history, transcripts, reports, logs, model caches or credentials.
  Use only the original fictional OrbitDesk content for demos and tests. Inspect staged files and
  history before publishing. Do not force-push or overwrite other work.
- Preserve original-project MIT license and third-party notices (edge-tts is LGPLv3).
- Check: `python -m ruff check .`, `python -m ruff format --check .`,
  `python -m pytest -q -m "not gui"`, and `xvfb-run -a python -m pytest -q -m gui` on Linux.
- Windows physical microphone, native GUI, Edge playback, SAPI voices and real local Codex login
  remain manual checks until tested on a Windows machine. Keep README and docs/VALIDATION.md honest.
- Update README and validation evidence with behavior changes. Keep Git commits focused and
  use a branch/PR if protection requires it. No Windows executable build until explicitly requested.
