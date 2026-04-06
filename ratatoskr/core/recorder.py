"""Ratatoskr – microphone recorder using sounddevice."""

import os
import wave
import threading
from typing import Optional

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16_000  # 16 kHz — optimal for Whisper
CHANNELS = 1
DTYPE = "int16"

_RECOVERY_DIR = os.path.join(os.path.expanduser("~"), ".ratatoskr")
RECOVERY_PATH = os.path.join(_RECOVERY_DIR, "recovery.wav")


def save_recovery_wav(audio: np.ndarray) -> None:
    """Write float32 audio to the recovery WAV file."""
    os.makedirs(_RECOVERY_DIR, exist_ok=True)
    int16 = (audio * 32768).clip(-32768, 32767).astype(np.int16)
    with wave.open(RECOVERY_PATH, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int16.tobytes())


def load_recovery_wav() -> Optional[np.ndarray]:
    """Load recovery WAV and return float32 array, or None if missing."""
    if not os.path.isfile(RECOVERY_PATH):
        return None
    try:
        with wave.open(RECOVERY_PATH, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        int16 = np.frombuffer(raw, dtype=np.int16)
        return int16.astype(np.float32) / 32768.0
    except Exception:
        return None


def delete_recovery_wav() -> None:
    """Remove the recovery file if it exists."""
    try:
        os.unlink(RECOVERY_PATH)
    except OSError:
        pass


class Recorder:
    """Records audio from the default microphone, returns float32 numpy array."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: Optional[sd.InputStream] = None
        self._recording = threading.Event()
        self._paused = threading.Event()
        self._total_frames = 0

    @property
    def is_recording(self) -> bool:
        return self._recording.is_set()

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    def start(self) -> None:
        """Start recording from the default input device.

        Raises on failure (e.g. no mic, access denied) so the caller can
        notify the user.  Internal state is kept consistent on error.
        """
        if self._recording.is_set():
            return
        self._chunks.clear()
        self._total_frames = 0
        self._paused.clear()

        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                callback=self._audio_callback,
            )
            stream.start()
        except Exception:
            self._recording.clear()
            raise

        self._stream = stream
        self._recording.set()

    def pause(self) -> None:
        """Pause recording (keep stream open, stop collecting audio)."""
        if self._recording.is_set():
            self._paused.set()

    def resume(self) -> None:
        """Resume recording after pause."""
        if self._recording.is_set():
            self._paused.clear()

    def stop(self) -> Optional[np.ndarray]:
        """Stop recording and return float32 mono audio array, or None if empty."""
        if not self._recording.is_set():
            return None
        self._recording.clear()
        self._paused.clear()

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._chunks:
            return None

        audio = np.concatenate(self._chunks, axis=0)
        self._chunks.clear()

        # faster-whisper expects float32 in [-1, 1]
        return audio.flatten().astype(np.float32) / 32768.0

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            print(f"[recorder] audio status: {status}", flush=True)
        if self._recording.is_set() and not self._paused.is_set():
            self._chunks.append(indata.copy())
            self._total_frames += indata.shape[0]

    @property
    def duration(self) -> float:
        """Approximate duration of current recording in seconds (O(1))."""
        return self._total_frames / SAMPLE_RATE
