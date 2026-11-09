# 验证记录与 Windows 本机验收

日期：2026-11-09（北京时间）。开发在 Linux 云端工作区完成，没有在公司 Windows 电脑创建项目文件。

## 云端实际执行

- Python **3.11.17**，独立虚拟环境，按 requirements-dev.txt 安装依赖。
- 核心测试 **32 项通过**，GUI Mock 测试 **5 项通过**，共 **37 项通过**。
- Tkinter 测试使用 Python 3.11.17 / Tk 9.0 的云端 X11 虚拟显示，不是 Windows。测试覆盖虚构 PPT 导入、逐页草稿、文本多轮对话、历史保存、报告导出、API 失败保留原文、录音/转写流程及临时音频删除。
- `python -m ruff check .` 与 `python -m ruff format --check .` 通过。
- 核心测试现场生成 PPTX，实际解析标题、组合形状文字、表格和备注；实际读写 WAV、JSON 和 Markdown。模拟音频为程序生成的数字采样，不是真人录音。
- Codex 使用 Mock 验证 subprocess 参数、标准输入、多轮上下文、结构化输出、超时和错误响应；**未实际发起模型/API 请求**。
- Whisper 使用 Mock 检查 CPU、int8、英语、离线缓存和错误处理；**未下载实际 Whisper 权重、未测试真实识别质量**。
- TTS 测试模拟 Edge 失败和本地回退、取消旧请求；**未调用在线语音或 Windows SAPI**。
- Windows x64 / CPython 3.11 锁定清单中的 **43 个运行依赖包均成功下载**到 Linux 云端临时目录，并检查许可证元数据。这一步未执行 Windows 二进制；另见下方 GitHub Actions 实际安装和测试结果。
- 核对本机云端 `codex exec --help` 支持使用的参数；这不证明用户家中 Windows 的 CLI 版本及认证可用。
- `ui-preview.png` 来自系统 Python 3.13.5 / Tk 8.6 的实际 Tk 窗口（字体渲染预览），只有原创虚构内容和明确标记的 Mock 回复，没有真实用户资料。自动化测试仍使用目标 Python 3.11，预览的辅助渲染器版本不作为支持版本声明。

核心检查命令：

```text
python -m pytest -q -m "not gui"
DISPLAY=:99 python -m pytest -q -m gui
python -m ruff check .
python -m ruff format --check .
```

标准 Linux 环境也可使用 `xvfb-run -a python -m pytest -q`。GitHub Actions 定义 Linux/Windows 核心测试及 Linux 虚拟显示 GUI 测试，具体远程执行情况以仓库 Actions 为准，不把尚未执行的配置当作通过结果。

## GitHub 发布后补充验证

源码提交 `3e576192add5904b55f02f1853e4f61d53f758cf` 的
[GitHub Actions #42588829272](https://github.com/ZJJUP/PPT-AI-Coach/actions/runs/42588829272)
已实际完成，结论为 **success**：

- `windows-latest` / Python 3.11：依赖安装、Ruff 检查、格式检查通过；**32 passed, 5 deselected**（GUI 测试在 Windows CI 中不执行）。
- `ubuntu-latest` / Python 3.11：同样的核心检查通过，**32 passed**；Xvfb 下 GUI Mock 测试 **5 passed**。
- 推送后重新从 Public 仓库 clone，核对远程与本地提交一致，37 个文件齐全，Git 对象完整性检查通过。
- 实际下载 Public 仓库的 main.zip，与提交内容逐文件核对；`start.bat` 按 .gitattributes 使用 Windows CRLF，其他文件内容一致。
- 暂存区和现有完整历史的凭据特征/禁止文件类型检查未发现问题；没有上传 PPT、真实录音、会话 JSON、模型、缓存、环境或认证信息。

Windows CI 安装/核心 Mock 测试通过，仅说明其托管运行器上的这些检查通过；**不代表家中物理麦克风、原生 GUI、TTS、Whisper 真实识别或私人 Codex 登录已验证**。下表保持待本机验收状态。

## 仍待家中 Windows 实机验证

| 项目 | 验收步骤 | 预期 |
| --- | --- | --- |
| Python/Tk | 官方 Python 3.11 x64，`py -3.11 -m tkinter` | 弹出窗口，文字显示正常 |
| 安装和启动 | 按 README 建 .venv、装锁定清单、双击 start.bat | 无依赖/DLL 错误，界面正常 |
| 中文与 DPI | 100% / 150% 缩放检查、调整窗口大小 | 按钮可用，无重要内容遮挡 |
| PPT | 导入原创虚构示例，再用自己有权使用的 PPT | 页码、正文、表格和可获取备注正确 |
| 麦克风 | 开权限，刷新设备，录 10 秒英语；再禁用设备重试 | 正常有转写，失败有提示且可恢复 |
| 模型下载/离线 | 下载 base.en，再用 --offline 加载 | 下载成功，断网可加载缓存模型 |
| 真实识别 | 用英语录短句，检查姓名/术语，手工修正 | 无声/空结果有提示，识别可读；不承诺准确率 |
| Codex | `codex login status`，终端调用，再界面发送 | 复用私人账号，无需在软件中输入凭据 |
| Windows CLI | 分别验证 codex.cmd 或原生 .exe、沙箱配置 | 参数兼容，正常结束，无遗留持续调用 |
| 多轮 | 演讲后切讨论，回答同一页追问，再切页 | 回复能引用最近对话，页码不混乱 |
| 语音 | auto 听反馈，再 local，开始录音时停止朗读 | Edge 或 SAPI 可听，设备和英语语音包可用 |
| 网络失败 | 断网调用 Codex/Edge，再恢复 | 无崩溃，保留待发送文本；可用本地语音/文字 |
| 历史和报告 | 多页练习，导出 .md，重启后开 JSON | 全部逐页记录存在，未练习页明确，能继续 |
| 数据清理 | 检查用户数据目录、正常退出后临时目录 | 历史只在本机，无录音被提交到 Git |

这些项目当前均为 **待验证**，云端 Mock 通过不代表它们通过。原生 Windows API、音频驱动、语音包、网络、账号权限和 GUI 外观都依赖实际机器。

## 发布内容检查

发布前检查暂存区、文件类型、diff 和所有提交历史。只允许原创源码、测试、文档、MIT License、CI 以及虚构界面截图；禁止公司/客户文档、用户 PPT、真实录音/转写、环境、缓存、日志和认证文件。依赖许可见 THIRD_PARTY_NOTICES.md 和 DEPENDENCY_LICENSES.md。

远程推送后应对照 commit/tree 校验文件完整性，确认 Public 与默认分支，并核对远程分支 SHA。任何尚待本机验证的项目应继续保持此状态，直到真实完成验收并补充证据。
