from __future__ import annotations

import json
import queue
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .audio import Recorder, input_devices
from .codex_client import CodexClient
from .demo import create_demo
from .errors import CoachError
from .models import Session, Turn
from .presentation import load_presentation
from .report import export_report
from .speech import SpeechService
from .storage import HistoryStore, atomic_json, data_dir
from .transcription import MODEL_NAMES, Transcriber


class CoachApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PPT-AI-Coach · English presentation practice")
        self.root.geometry("1180x840")
        self.root.minsize(900, 700)
        self.session: Session | None = None
        self.page = 0
        self.drafts = {}
        self.state = "idle"
        self.closed = False
        self.events = queue.Queue()
        self.controls = []
        self.recorder = Recorder()
        self.speech = SpeechService()
        self.history = HistoryStore()
        self.transcriber = None
        self.started_recording = 0.0
        self.device_map = {"系统默认麦克风": None}
        self.mode = tk.StringVar(value="presentation")
        self.status = tk.StringVar(value="导入 PPTX 或打开虚构演示，开始英语演讲练习。")
        self.page_label = tk.StringVar(value="尚未导入 PPTX")
        self.page_choice = tk.StringVar()
        self.whisper_model = tk.StringVar(value="base.en")
        self.offline = tk.BooleanVar(value=False)
        self.codex_path = tk.StringVar()
        self.codex_model = tk.StringVar()
        self.voice_mode = tk.StringVar(value="auto")
        self.device = tk.StringVar(value="系统默认麦克风")
        self.auto_send = tk.BooleanVar(value=False)
        self._build()
        self._load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.root.after(100, self._poll)

    def _button(self, parent, label, command, **kwargs):
        widget = ttk.Button(parent, text=label, command=command, **kwargs)
        self.controls.append(widget)
        return widget

    def _build(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TButton", padding=(9, 5))
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Sub.TLabel", foreground="#506078")
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        heading = ttk.Frame(outer)
        heading.pack(fill="x")
        ttk.Label(heading, text="PPT-AI-Coach", style="Title.TLabel").pack(side="left")
        ttk.Label(heading, text="英语演讲 · 客户问答 · 逐页复盘", style="Sub.TLabel").pack(
            side="left", padx=18
        )
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(12, 8))
        for label, command in [
            ("导入 PPTX", self.import_deck),
            ("虚构演示", self.open_demo),
            ("打开历史", self.open_history),
            ("结束并导出报告", self.export),
        ]:
            self._button(toolbar, label, command).pack(side="left", padx=(0, 8))
        ttk.Label(
            outer,
            text="发送时，当前页内容（含备注）、演讲文本及最近 8 轮对话将交给 Codex。"
            "自动语音使用在线 Edge TTS，可在设置中改为本地。",
            wraplength=1100,
            style="Sub.TLabel",
        ).pack(fill="x", pady=(0, 8))
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)
        practice = ttk.Frame(self.tabs, padding=10)
        settings = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(practice, text="  练习工作台  ")
        self.tabs.add(settings, text="  设置与设备  ")
        navigation = ttk.Frame(practice)
        navigation.pack(fill="x", pady=(0, 8))
        self._button(navigation, "上一页", lambda: self.navigate(-1)).pack(side="left")
        ttk.Label(navigation, textvariable=self.page_label).pack(side="left", padx=12)
        self._button(navigation, "下一页", lambda: self.navigate(1)).pack(side="left")
        ttk.Label(navigation, text="跳转到页").pack(side="left", padx=(16, 4))
        self.page_box = ttk.Combobox(
            navigation, textvariable=self.page_choice, state="readonly", width=6
        )
        self.page_box.pack(side="left")
        self.page_box.bind("<<ComboboxSelected>>", self._jump)
        self.controls.append(self.page_box)
        for label, value in [("演讲模式", "presentation"), ("讨论模式", "discussion")]:
            radio = ttk.Radiobutton(navigation, text=label, variable=self.mode, value=value)
            radio.pack(side="right", padx=8)
            self.controls.append(radio)
        panels = ttk.Panedwindow(practice, orient="horizontal")
        panels.pack(fill="both", expand=True)
        left, right = ttk.Frame(panels), ttk.Frame(panels)
        panels.add(left, weight=1)
        panels.add(right, weight=1)
        ttk.Label(left, text="当前页面 · 标题 / 正文 / 表格 / 备注").pack(anchor="w", pady=4)
        self.slide_text = scrolledtext.ScrolledText(
            left, wrap="word", width=50, height=14, font=("Segoe UI", 11), padx=10, pady=10
        )
        self.slide_text.pack(fill="both", expand=True, padx=(0, 8))
        self.slide_text.configure(state="disabled")
        ttk.Label(right, text="Coach & customer · 当前页对话").pack(anchor="w", pady=4)
        self.conversation = scrolledtext.ScrolledText(
            right, wrap="word", width=52, height=14, font=("Segoe UI", 11), padx=10, pady=10
        )
        self.conversation.pack(fill="both", expand=True)
        self.conversation.configure(state="disabled")
        ttk.Label(
            practice, text="你的英语讲解 / 回答（录音转写后可修改，也可直接输入；发送后清空）"
        ).pack(anchor="w", pady=(10, 4))
        self.transcript = scrolledtext.ScrolledText(
            practice, height=5, wrap="word", font=("Segoe UI", 11), padx=8, pady=6
        )
        self.transcript.pack(fill="x")
        actions = ttk.Frame(practice)
        actions.pack(fill="x", pady=(8, 0))
        self._button(actions, "开始录音", self.start_recording).pack(side="left", padx=(0, 6))
        self.stop_button = ttk.Button(actions, text="停止并转写", command=self.stop_recording)
        self.stop_button.pack(side="left", padx=(0, 6))
        self.stop_button.configure(state="disabled")
        self._button(actions, "发送给教练", self.send).pack(side="left", padx=(0, 6))
        self._button(actions, "重听追问", self.replay).pack(side="left", padx=(0, 6))
        ttk.Button(actions, text="停止朗读", command=self.speech.stop).pack(side="left")
        ttk.Label(actions, text="单次录音最多 5 分钟", style="Sub.TLabel").pack(side="right")
        self._build_settings(settings)
        ttk.Separator(outer).pack(fill="x", pady=(10, 6))
        ttk.Label(outer, textvariable=self.status, wraplength=1100).pack(fill="x")

    def _build_settings(self, frame):
        frame.columnconfigure(1, weight=1)
        rows = [
            ("Whisper 模型", self.whisper_model, MODEL_NAMES),
            ("Codex 可执行文件（留空自动查找）", self.codex_path, None),
            ("Codex 模型（留空使用 CLI 默认）", self.codex_model, None),
            (
                "语音：auto 在线优先 / local 本地 / off 关闭",
                self.voice_mode,
                ("auto", "local", "off"),
            ),
            ("麦克风", self.device, tuple(self.device_map)),
        ]
        for row, (label, variable, choices) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=8, padx=(0, 14))
            if choices:
                widget = ttk.Combobox(
                    frame, textvariable=variable, values=choices, state="readonly"
                )
            else:
                widget = ttk.Entry(frame, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", pady=8)
            self.controls.append(widget)
            if variable is self.device:
                self.device_box = widget
        self._button(frame, "刷新麦克风列表", self.refresh_devices).grid(row=4, column=2, padx=8)
        for row, label, variable in [
            (5, "Whisper 离线：仅使用已下载模型", self.offline),
            (6, "转写后自动发送给 Codex（默认关闭，便于先检查文本）", self.auto_send),
        ]:
            widget = ttk.Checkbutton(frame, text=label, variable=variable)
            widget.grid(row=row, column=0, columnspan=3, sticky="w", pady=10)
            self.controls.append(widget)
        self._button(frame, "保存设置", self.save_settings).grid(
            row=7, column=0, sticky="w", pady=12
        )
        ttk.Label(
            frame,
            text="演讲模式：改善表达结构，并提出客户问题。\n"
            "讨论模式：评价你对上一个问题的回答，并继续追问。\n\n"
            "Whisper 在本机 CPU 上运行，首次下载模型需要网络。\n"
            "Codex 复用你私人电脑上已经安装并登录的 CLI；这里不提供密码或 Token 输入框。\n"
            "本地语音需要 Windows 英语语音包。语音失败时仍可阅读文字并继续练习。\n\n"
            f"私人数据目录：{data_dir()}\n历史含 PPT 提取文本与演讲记录，请自行管理和删除。",
            wraplength=940,
            justify="left",
            style="Sub.TLabel",
        ).grid(row=8, column=0, columnspan=3, sticky="nw", pady=10)

    def _load_settings(self):
        path = data_dir() / "settings.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, variable in self._settings_vars().items():
                value = data.get(key)
                if key in {"offline", "auto_send"}:
                    if isinstance(value, bool):
                        variable.set(value)
                elif isinstance(value, str) and len(value) <= 1024:
                    if key == "whisper_model" and value not in MODEL_NAMES:
                        continue
                    if key == "voice_mode" and value not in {"auto", "local", "off"}:
                        continue
                    variable.set(value)
        except (OSError, ValueError, AttributeError):
            self.status.set("本地设置无法读取，已使用默认值；可重新保存设置。")

    def _settings_vars(self):
        return {
            key: getattr(self, key)
            for key in (
                "whisper_model",
                "offline",
                "auto_send",
                "codex_path",
                "codex_model",
                "voice_mode",
            )
        }

    def save_settings(self):
        try:
            atomic_json(
                data_dir() / "settings.json",
                {key: variable.get() for key, variable in self._settings_vars().items()},
            )
            self.status.set("设置已保存（不包含认证信息）。")
        except OSError:
            self._error(CoachError("设置保存失败，请检查用户目录权限。"))

    def _set_state(self, state: str, message: str = ""):
        self.state = state
        for widget in self.controls:
            widget.state(["!disabled"] if state == "idle" else ["disabled"])
        self.stop_button.configure(state="normal" if state == "recording" else "disabled")
        self.transcript.configure(state="normal" if state == "idle" else "disabled")
        if message:
            self.status.set(message)

    def _work(self, message, task, done):
        if self.state != "idle":
            return
        self._set_state("working", message)

        def run():
            try:
                value = task()
                self.events.put((done, value, None))
            except Exception as exc:
                self.events.put((None, None, exc))

        threading.Thread(target=run, daemon=True).start()

    def _poll(self):
        if self.closed:
            return
        try:
            while True:
                done, value, error = self.events.get_nowait()
                if done == "speech":
                    if self.state == "idle":
                        self.status.set(value)
                    continue
                self._set_state("idle")
                if error:
                    self._error(error)
                elif done:
                    try:
                        done(value)
                    except Exception as exc:
                        self._error(exc)
        except queue.Empty:
            pass
        if self.state == "recording":
            seconds = int(time.monotonic() - self.started_recording)
            self.status.set(
                f"正在录音 {seconds // 60:02d}:{seconds % 60:02d} / 05:00，结束后点击停止。"
            )
            if self.recorder.limit_reached.is_set():
                self.stop_recording()
        self._poll_id = self.root.after(100, self._poll)

    def _error(self, error):
        text = (
            str(error)
            if isinstance(error, CoachError)
            else ("操作失败，请检查依赖安装、数据目录权限及设备连接。可关闭程序后在终端重新启动。")
        )
        self.status.set(text)
        messagebox.showerror("PPT-AI-Coach", text, parent=self.root)

    @staticmethod
    def _replace(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _show_page(self):
        if not self.session:
            return
        slide = self.session.slides[self.page]
        self.page_label.set(f"第 {slide.number} / {len(self.session.slides)} 页")
        self.page_box.configure(values=[str(s.number) for s in self.session.slides])
        self.page_choice.set(str(slide.number))
        self._replace(self.slide_text, slide.text())
        turns = [turn for turn in self.session.turns if turn.slide_number == slide.number]
        text = "\n\n────────────────────\n\n".join(
            f"YOU [{turn.mode}]\n{turn.transcript}\n\n{turn.reply.text()}" for turn in turns
        )
        self._replace(self.conversation, text or "讲解这一页，或先输入一段英语，再发送给教练。")
        self.conversation.see("end")

    def _new_session(self, session):
        self.speech.stop()
        self.session, self.page = session, 0
        self.drafts = {}
        self.transcript.delete("1.0", "end")
        self._show_page()
        self.tabs.select(0)
        self.status.set(f"已打开 {session.deck_name}，共 {len(session.slides)} 页。")

    def import_deck(self):
        if self.state != "idle":
            return
        path = filedialog.askopenfilename(filetypes=[("PowerPoint presentation", "*.pptx")])
        if path:
            self._work(
                "正在解析 PPTX…",
                lambda: Session(Path(path).name, load_presentation(Path(path))),
                self._new_session,
            )

    def open_demo(self):
        def task():
            with tempfile.TemporaryDirectory(prefix="ppt-coach-demo-") as directory:
                path = create_demo(Path(directory) / "OrbitDesk-demo.pptx")
                return Session(path.name, load_presentation(path))

        self._work("正在生成虚构产品演示…", task, self._new_session)

    def open_history(self):
        if self.state != "idle":
            return
        path = filedialog.askopenfilename(
            initialdir=str(self.history.root), filetypes=[("Practice history", "*.json")]
        )
        if path:
            self._work("正在读取历史…", lambda: self.history.load(Path(path)), self._new_session)

    def navigate(self, delta):
        if self.session and self.state == "idle":
            self.speech.stop()
            self.drafts[self.page] = self.transcript.get("1.0", "end").strip()
            self.page = min(max(self.page + delta, 0), len(self.session.slides) - 1)
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", self.drafts.get(self.page, ""))
            self._show_page()

    def _jump(self, event=None):
        if self.session and self.state == "idle":
            self.speech.stop()
            self.drafts[self.page] = self.transcript.get("1.0", "end").strip()
            self.page = int(self.page_choice.get()) - 1
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", self.drafts.get(self.page, ""))
            self._show_page()

    def refresh_devices(self):
        def done(devices):
            self.device_map = {"系统默认麦克风": None}
            self.device_map.update({f"{index}: {name}": index for index, name in devices})
            self.device_box.configure(values=list(self.device_map))
            self.device.set("系统默认麦克风")
            self.status.set(f"已发现 {len(devices)} 个录音输入设备。")

        self._work("正在检测麦克风…", input_devices, done)

    def start_recording(self):
        if not self.session:
            messagebox.showinfo("开始练习", "请先导入 PPTX 或打开虚构演示。")
            return
        self.speech.stop()
        device = self.device_map.get(self.device.get())

        def started(_):
            self.started_recording = time.monotonic()
            self._set_state("recording", "正在录音…")

        self._work("正在启动麦克风…", lambda: self.recorder.start(device), started)

    def stop_recording(self):
        if self.state != "recording":
            return
        self._set_state("idle")
        model, offline = self.whisper_model.get(), self.offline.get()
        auto_send = self.auto_send.get()

        def task():
            with tempfile.TemporaryDirectory(prefix="ppt-coach-audio-") as directory:
                path = Path(directory) / "recording.wav"
                self.recorder.stop_to_file(path)
                if (
                    self.transcriber is None
                    or self.transcriber.model_name != model
                    or self.transcriber.offline != offline
                ):
                    self.transcriber = Transcriber(model, offline)
                return self.transcriber.transcribe(path)

        def done(text):
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", text)
            self.status.set("转写完成，临时录音已删除。可修改文本后发送给教练。")
            if auto_send:
                self.send()

        self._work("正在转写英语（首次可能下载模型，请稍候）…", task, done)

    def _client(self):
        return CodexClient(self.codex_path.get(), self.codex_model.get())

    def send(self):
        if not self.session or self.state != "idle":
            return
        text = self.transcript.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("发送给教练", "请先录音或输入英语讲解。")
            return
        session, slide, mode = self.session, self.session.slides[self.page], self.mode.get()
        client = self._client()
        self.speech.stop()

        def done(reply):
            session.turns.append(Turn(slide.number, mode, text, reply))
            session.overall = ""
            saved = True
            try:
                self.history.save(session)
            except CoachError as exc:
                saved = False
                self._error(exc)
            self.transcript.delete("1.0", "end")
            self.drafts.pop(self.page, None)
            self._show_page()
            self.status.set(
                "收到教练反馈，历史已保存在本机。可用麦克风继续回答。"
                if saved
                else "收到反馈，但历史保存失败。请立即导出报告以保留本次内容。"
            )
            self._speak(reply.text())

        self._work(
            "Codex 正在分析当前页与演讲内容…",
            lambda: client.coach(slide, text, session.turns, mode),
            done,
        )

    def _speak(self, text):
        mode = self.voice_mode.get()
        if mode == "off":
            return
        cancel = self.speech.new_request()

        # Speech events are status-only and cannot unlock an active recording/API job.
        def run():
            try:
                notice = self.speech.speak(text, mode, cancel=cancel)
                if notice:
                    self.events.put(("speech", notice, None))
            except CoachError as exc:
                self.events.put(("speech", str(exc), None))

        threading.Thread(target=run, daemon=True).start()

    def replay(self):
        if not self.session:
            return
        turns = [t for t in self.session.turns if t.slide_number == self.page + 1]
        if turns:
            self.speech.stop()
            self._speak(turns[-1].reply.question)

    def export(self):
        if not self.session or not self.session.turns:
            messagebox.showinfo("导出报告", "请先完成至少一轮练习。")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile="practice-report.md",
            filetypes=[("Markdown report", "*.md")],
            initialdir=str(data_dir()),
        )
        if not path:
            return
        session, client = self.session, self._client()

        def task():
            warning = ""
            try:
                session.overall = client.summarize(session)
            except CoachError:
                session.overall = ""
                warning = "整体 AI 总结不可用，已保留逐页反馈与通用练习建议。"
            export_report(session, Path(path))
            try:
                self.history.save(session)
            except CoachError:
                warning += " 历史保存失败，Markdown 报告已保存。"
            return warning

        def done(warning):
            self.status.set(f"报告已保存：{path}。{warning}")
            messagebox.showinfo("报告已导出", f"{path}\n{warning}")

        self._work("正在生成整体改进计划并导出 Markdown…", task, done)

    def close(self):
        if self.state != "idle" and not messagebox.askyesno(
            "退出", "当前仍在录音或处理，退出将放弃未完成任务。是否退出？", parent=self.root
        ):
            return
        self.closed = True
        self.root.after_cancel(self._poll_id)
        self.speech.stop()
        try:
            self.recorder.abort()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    CoachApp(root)
    root.mainloop()
