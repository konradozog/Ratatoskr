"""Ratatoskr – transcriber engine (faster-whisper, simplified for voice memos)."""

import threading
from typing import Optional, Callable, List

import numpy as np


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


def collect_chunks(
    audio: np.ndarray,
    chunks: List[dict],
    sampling_rate: int = 16000,
    max_duration: float = float("inf"),
):
    """faster-whisper 1.2.1's ``vad.collect_chunks`` with the same output, minus
    its quadratic cost.

    Upstream grows the speech audio by one ``np.concatenate`` per VAD chunk, so
    every chunk copies all the speech before it. With our 300 ms silence
    threshold a 30 min memo has ~450 chunks and waited ~9 s before transcription
    started (60 min: ~30 s). Here the slices are collected in a list and
    concatenated once per output chunk.
    """
    if not chunks:
        return [np.array([], dtype=np.float32)], [{"offset": 0, "duration": 0, "segments": []}]

    audio_chunks = []
    chunks_metadata = []
    pieces, segments, current, total = [], [], 0, 0

    for chunk in chunks:
        length = chunk["end"] - chunk["start"]
        if current + length > max_duration * sampling_rate:
            audio_chunks.append(np.concatenate(pieces) if pieces else np.array([], dtype=np.float32))
            chunks_metadata.append(
                {"offset": total / sampling_rate, "duration": current / sampling_rate, "segments": segments}
            )
            total += current
            pieces, segments, current = [], [], 0
            # as upstream: a chunk that opens a new output chunk is not listed in its segments
            pieces.append(audio[chunk["start"]:chunk["end"]])
            current = length
        else:
            segments.append(chunk)
            pieces.append(audio[chunk["start"]:chunk["end"]])
            current += length

    audio_chunks.append(np.concatenate(pieces) if pieces else np.array([], dtype=np.float32))
    chunks_metadata.append(
        {"offset": total / sampling_rate, "duration": current / sampling_rate, "segments": segments}
    )
    return audio_chunks, chunks_metadata


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

                import faster_whisper.transcribe
                from faster_whisper import WhisperModel

                faster_whisper.transcribe.collect_chunks = collect_chunks
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
