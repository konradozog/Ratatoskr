# Ratatoskr

Press a hotkey, speak, get text. That's it.

Ratatoskr is a tiny Windows app that sits in your system tray and turns speech into text using [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Everything runs locally on your machine — no audio is sent anywhere, no cloud APIs, no accounts.

![Recording overlay](ratatoskr/assets/overlay.png)

## How it works

1. Press `Ctrl+Alt+R` (configurable)
2. A small overlay appears in the corner with pause and stop buttons
3. Talk
4. Press the hotkey again or click stop on the overlay
5. Transcription is copied to your clipboard — paste it wherever you want

## Install

```bash
git clone https://github.com/konradozog/Ratatoskr.git
cd Ratatoskr
python -m venv .venv
.venv\Scripts\activate
pip install .
```

Requires **Windows 10/11** and **Python 3.10+**.

For faster transcription with a GPU, install CUDA libraries compatible with [CTranslate2](https://github.com/OpenNMT/CTranslate2).

## Run

```bash
ratatoskr
```

The app starts minimized in the system tray. Right-click the tray icon for settings.

## Settings

| Option | Default | Description |
|--------|---------|-------------|
| Model | `small` | Whisper model size (tiny / base / small / medium / large-v3) |
| Language | auto | Source language or auto-detect |
| Hotkey | `Ctrl+Alt+R` | Global keyboard shortcut |
| Copy to clipboard | on | Auto-copy transcription |
| Save to file | off | Save `.txt` to `~/.ratatoskr/transcripts/` |

Smaller models are faster but less accurate. `small` is a good default for most languages.

## Privacy

All processing happens on your machine. Ratatoskr uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (a local Whisper implementation) — no audio leaves your computer, ever. The only network activity is the one-time model download from Hugging Face on first run.

## Third-party licenses

| Dependency | License |
|------------|---------|
| [PySide6](https://doc.qt.io/qtforpython/) | LGPL-3.0 |
| [shiboken6](https://doc.qt.io/qtforpython/) | LGPL-3.0 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT |
| [sounddevice](https://python-sounddevice.readthedocs.io/) | MIT |
| [NumPy](https://numpy.org/) | BSD-3-Clause |
| [huggingface-hub](https://github.com/huggingface/huggingface_hub) | Apache-2.0 |
| [tokenizers](https://github.com/huggingface/tokenizers) | Apache-2.0 |
| [PyAV](https://pyav.basswood-io.com/) | BSD-3-Clause |
| [ONNX Runtime](https://onnxruntime.ai/) | MIT |

PySide6/shiboken6 are used under LGPL-3.0 via dynamic linking. You are free to replace them with any compatible Qt binding.

## License

MIT — see [LICENSE](LICENSE)
