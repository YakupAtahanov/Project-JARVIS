import threading
import numpy as np
import torch
import whisper
import speech_recognition as sr

from queue import Queue, Empty
from datetime import datetime, timedelta
from typing import Callable, Generator, Optional, Tuple

class SpeechToText:
    """
    Real-time, offline speech-to-text using SpeechRecognition for mic capture
    and openai-whisper for transcription.

    Usage:
        stt = SpeechToText(model="base", english_only=True)
        stt.start()
        try:
            for text, is_final in stt.iter_results():
                print(("FINAL: " if is_final else "PARTIAL: ") + text)
        finally:
            stt.stop()
    """

    def __init__(
        self,
        model: str = "base",
        english_only: bool = True,
        energy_threshold: int = 1000,
        record_timeout: float = 2.0,
        phrase_timeout: float = 3.0,
        sample_rate: int = 16000,
        mic_name_substring: Optional[str] = None,  # None = default device
        adjust_ambient_seconds: float = 0.5,
        enable_fp16_if_cuda: bool = True,
    ):
        self.model_name = model + (".en" if (english_only and model != "large") else "")
        self.energy_threshold = energy_threshold
        self.record_timeout = float(record_timeout)
        self.phrase_timeout = float(phrase_timeout)
        self.sample_rate = int(sample_rate)
        self.mic_name_substring = mic_name_substring
        self.adjust_ambient_seconds = adjust_ambient_seconds
        self.fp16 = (enable_fp16_if_cuda and torch.cuda.is_available())

        # I/O queues
        self._audio_q: Queue[bytes] = Queue()        # raw audio from SR callback
        self._result_q: Queue[Tuple[str, bool]] = Queue()  # (text, is_final)

        # SR + mic state
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = self.energy_threshold
        self._recognizer.dynamic_energy_threshold = False
        self._mic: Optional[sr.Microphone] = None
        self._stop_listening = None  # SR's returned stopper

        # Whisper model
        self._wmodel = None

        # Processing thread state
        self._worker_thread: Optional[threading.Thread] = None
        self._running = threading.Event()

        # Transcription state
        self._phrase_time: Optional[datetime] = None
        self._phrase_bytes = bytearray()
        self._last_emitted_text = ""  # for coalescing partials

        # Optional callback for push updates
        self._on_update: Optional[Callable[[str, bool], None]] = None

    @staticmethod
    def list_microphones() -> None:
        print("Available microphone devices:")
        for idx, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"[{idx}] {name}")

    def _pick_microphone(self) -> sr.Microphone:
        if self.mic_name_substring:
            for idx, name in enumerate(sr.Microphone.list_microphone_names()):
                if self.mic_name_substring.lower() in (name or "").lower():
                    return sr.Microphone(sample_rate=self.sample_rate, device_index=idx)
            raise RuntimeError(f"Microphone containing '{self.mic_name_substring}' not found.")
        return sr.Microphone(sample_rate=self.sample_rate)

    def on_update(self, cb: Callable[[str, bool], None]) -> None:
        """Register a callback called as `cb(text, is_final)`."""
        self._on_update = cb

    def start(self) -> None:
        """Load model, open mic, start background capture and processing."""
        if self._running.is_set():
            return
        # Load whisper
        self._wmodel = whisper.load_model(self.model_name)

        # Mic
        self._mic = self._pick_microphone()
        with self._mic as source:
            # Quick ambient calibration to keep VAD sane
            self._recognizer.adjust_for_ambient_noise(source, duration=self.adjust_ambient_seconds)

        # Background capture -> _audio_q
        def _record_cb(_, audio: sr.AudioData):
            try:
                data = audio.get_raw_data()
                self._audio_q.put_nowait(data)
            except Exception:
                pass

        self._stop_listening = self._recognizer.listen_in_background(
            self._mic, _record_cb, phrase_time_limit=self.record_timeout
        )

        # Worker thread: consumes _audio_q, runs Whisper, pushes (text, is_final) to _result_q
        self._running.set()
        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        """Stop capture and processing, free model."""
        if not self._running.is_set():
            return
        self._running.clear()

        if self._stop_listening:
            try:
                self._stop_listening(wait_for_stop=False)
            except Exception:
                pass
            self._stop_listening = None

        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            self._worker_thread = None

        # Close mic
        self._mic = None

        # Release model
        self._wmodel = None

        # Drain queues
        self._drain_queue(self._audio_q)
        self._drain_queue(self._result_q)

        # Reset state
        self._phrase_time = None
        self._phrase_bytes.clear()
        self._last_emitted_text = ""

    def _drain_queue(self, q: Queue) -> None:
        try:
            while True:
                q.get_nowait()
        except Empty:
            pass

    def _process_loop(self) -> None:
        """Main processing loop: buffer audio into phrases, transcribe, emit results."""
        while self._running.is_set():
            # Pull whatever audio is available without blocking
            got_any = False
            chunks: list[bytes] = []
            while True:
                try:
                    chunks.append(self._audio_q.get_nowait())
                    got_any = True
                except Empty:
                    break

            now = datetime.utcnow()
            phrase_complete = False

            if got_any:
                if self._phrase_time and (now - self._phrase_time) > timedelta(seconds=self.phrase_timeout):
                    # Too much silence -> new phrase
                    self._phrase_bytes.clear()
                    phrase_complete = True
                self._phrase_time = now
                # Append audio
                self._phrase_bytes.extend(b"".join(chunks))

                # Convert to float32 in [-1, 1]
                if self._phrase_bytes:
                    audio_np = np.frombuffer(self._phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                    # Transcribe current buffer
                    try:
                        result = self._wmodel.transcribe(audio_np, fp16=self.fp16)
                        text = (result.get("text") or "").strip()
                    except Exception as e:
                        text = f"[transcribe error: {e}]"

                    # Emit partial/final
                    if phrase_complete and text:
                        self._emit(text, is_final=True)
                        self._last_emitted_text = text
                    else:
                        # Only emit partial if it actually changed (reduces spam)
                        if text and text != self._last_emitted_text:
                            self._emit(text, is_final=False)
                            self._last_emitted_text = text
            else:
                # If no new audio and phrase_timeout elapsed, close out the phrase
                if self._phrase_time and (now - self._phrase_time) > timedelta(seconds=self.phrase_timeout):
                    if self._last_emitted_text:
                        self._emit(self._last_emitted_text, is_final=True)
                    self._phrase_bytes.clear()
                    self._phrase_time = None
                    self._last_emitted_text = ""
                # Don’t spin
                torch.cuda._sleep(10_000) if self.fp16 else None  # micro backoff; noop on CPU
                # Fallback tiny sleep:
                if not self.fp16:
                    threading.Event().wait(0.02)

    def _emit(self, text: str, is_final: bool) -> None:
        try:
            self._result_q.put_nowait((text, is_final))
        except Exception:
            pass
        if self._on_update:
            try:
                self._on_update(text, is_final)
            except Exception:
                pass

    def iter_results(self) -> Generator[Tuple[str, bool], None, None]:
        """Yield (text, is_final) as they arrive. Blocks."""
        while self._running.is_set():
            try:
                yield self._result_q.get(timeout=0.1)
            except Empty:
                continue

    def read(self, timeout: Optional[float] = None) -> Optional[Tuple[str, bool]]:
        """Pop one result (text, is_final). None if no result before `timeout`."""
        try:
            return self._result_q.get(timeout=timeout)
        except Empty:
            return None
