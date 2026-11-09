# Third-party licenses

PPT-AI-Coach's original source, tests, fictional OrbitDesk content and documentation
are MIT licensed. Dependencies are installed separately from upstream packages;
their copyrights and licenses are not replaced by this project's MIT license.
No dependency source, model weights or third-party presentation assets are vendored.

## Direct dependencies reviewed

| Component | Pinned version | Upstream license | Source |
| --- | --- | --- | --- |
| python-pptx | 1.0.2 | MIT | <https://github.com/scanny/python-pptx> |
| NumPy | 2.2.6 | BSD-3-Clause, bundled components have additional notices | <https://github.com/numpy/numpy> |
| sounddevice | 0.5.3 | MIT, PortAudio has a separate permissive license | <https://github.com/spatialaudio/python-sounddevice> |
| soundfile | 0.13.1 | BSD-3-Clause; libsndfile is LGPL-2.1-or-later | <https://github.com/bastibe/python-soundfile> |
| faster-whisper | 1.2.1 | MIT | <https://github.com/SYSTRAN/faster-whisper> |
| edge-tts | 7.2.3 | **LGPL-3.0** | <https://github.com/rany2/edge-tts> |

This review inspected installed package metadata and license files, including
the Windows wheels selected by `requirements-lock.txt`. All 43 runtime Python
distributions and their declared licenses are listed in
[docs/DEPENDENCY_LICENSES.md](docs/DEPENDENCY_LICENSES.md).
The listing is an inventory, not a replacement for original license text.

## Native libraries and model files

- Python and Tkinter/Tcl/Tk have their own PSF and Tcl/Tk licenses; supplied by
  the user's Python distribution, not this repository.
- CTranslate2 and ONNX Runtime use MIT licenses with notices for bundled components;
  Hugging Face Hub and tokenizers use Apache-2.0.
- PyAV is BSD-3-Clause. Its wheels can include FFmpeg libraries with separate
  LGPL/GPL and codec notices depending on the build. Inspect the exact wheel's
  build and upstream sources before redistributing its binaries.
- The Windows SoundFile wheel contains `_soundfile_data/COPYING` (LGPL 2.1 text)
  for libsndfile. Keep this and the upstream source/relinking requirements when
  redistributing binaries.
- NumPy's Windows wheel includes OpenBLAS notices and GCC runtime components
  covered by GPL with the GCC Runtime Library Exception. The exception and all
  bundled notices must be retained for binary redistribution.
- certifi declares MPL-2.0; tqdm includes MPL-2.0/MIT components. These licenses
  remain attached to those files. Other dependencies include MIT, BSD, Apache,
  PSF and associated permissive notices; see the complete inventory.
- Whisper model weights are downloaded by the user, never committed or bundled.
  OpenAI Whisper is MIT licensed; converted models retain their own model cards
  (for example <https://huggingface.co/Systran/faster-whisper-base.en>).
- Codex CLI is a separate user-installed program. This project calls it through
  a process boundary and does not redistribute its executable or authentication.
- Edge speech and Codex are online services subject to their providers' account
  and usage terms. An open-source code license does not grant service access.

## Source distribution versus a future EXE

Using unmodified LGPL libraries as separately installed, replaceable dependencies
does not require relicensing this project's independent original source under
LGPL. Users must still comply with each dependency's terms. This source release
does not redistribute dependencies or weights.

Before a future PyInstaller/portable binary release, review the exact resolved
packages and native builds again. Include copyright/license notices, required
source availability and replacement/relinking mechanisms (particularly LGPL
components), and applicable modifications' source. Do not simply attach the
project MIT license to a bundled executable and treat all components as MIT.

Development tools are not application runtime dependencies: pytest, Ruff and
pip-licenses use MIT; their dependencies retain their upstream licenses.

To repeat the metadata inventory in a developer environment:

```text
python -m pip install -r requirements-dev.txt
python -m piplicenses --with-urls --with-license-file
```

This assessment is based on upstream license declarations and inspected files,
not a legal opinion or a claim about every future dependency version.
