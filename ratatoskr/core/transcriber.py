"""Ratatoskr – transcriber engine (faster-whisper, simplified for voice memos)."""

import threading
from typing import Optional, Callable


# Models suitable for quick voice-to-text (speed vs accuracy trade-off)
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

_load_lock = threading.Lock()

LANGUAGES = {
    "auto": "Auto-detect",
    "pl": "Polish",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "uk": "Ukrainian",
    "cs": "Czech",
    "ru": "Russian",
    "ja": "Japanese",
    "zh": "Chinese",
    "ko": "Korean",
}


class TranscriberEngine:
    """Wraps faster-whisper for quick voice memo transcription."""

    def __init__(self):
        self._model = None
        self._model_name: str = ""
        self._device: str = ""
        self._compute_type: str = ""

    def load_model(
        self,
        model_name: str = "small",
        device: str = "auto",
        compute_type: str = "auto",
        on_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Load model in a background thread so the UI stays responsive."""

        def _do_load():
            with _load_lock:
                nonlocal device, compute_type

                if device == "auto":
                    try:
                        import ctranslate2
                        ctranslate2.get_supported_compute_types("cuda")
                        device = "cuda"
                    except Exception:
                        device = "cpu"

                if compute_type == "auto":
                    compute_type = "float16" if device == "cuda" else "int8"

                if (
                    self._model is not None
                    and self._model_name == model_name
                    and self._device == device
                    and self._compute_type == compute_type
                ):
                    if on_status:
                        on_status(f"Model {model_name} already loaded.")
                    return

                if on_status:
                    on_status(f"Loading model {model_name} on {device} ({compute_type})...")

                from faster_whisper import WhisperModel

                self._model = WhisperModel(model_name, device=device, compute_type=compute_type)
                self._model_name = model_name
                self._device = device
                self._compute_type = compute_type

                if on_status:
                    on_status(f"Model {model_name} ready ({device}/{compute_type}).")

        t = threading.Thread(target=_do_load, daemon=True)
        t.start()

    def transcribe(
        self,
        audio,
        language: Optional[str] = None,
        on_done: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Transcribe audio in background thread.

        *audio* can be a file path (str) or a float32 numpy array.
        Calls on_done(text) or on_error(msg).
        """

        def _run():
            try:
                # Wait for model loading to finish and grab a stable reference
                with _load_lock:
                    if self._model is None:
                        raise RuntimeError("Model not loaded.")
                    model = self._model

                lang = language if language and language != "auto" else None

                segments_iter, info = model.transcribe(
                    audio,
                    language=lang,
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=300,
                        threshold=0.5,
                        speech_pad_ms=30,
                    ),
                    beam_size=5,
                    word_timestamps=False,
                )

                text_parts = []
                for seg in segments_iter:
                    text_parts.append(seg.text.strip())

                full_text = " ".join(text_parts).strip()
                if on_done:
                    on_done(full_text)

            except Exception as e:
                if on_error:
                    on_error(str(e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def current_model_info(self) -> str:
        if self._model is None:
            return "No model loaded"
        return f"{self._model_name} ({self._device}/{self._compute_type})"
