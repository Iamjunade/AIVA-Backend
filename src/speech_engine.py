"""
AIVA - Speech Engine
======================
Combined speech recognition (Whisper), intent classification, and
text-to-speech (pyttsx3) for the conversational interface.

Speech Recognition: OpenAI Whisper 'small' model (offline capable)
Intent Classification: Rule-based keyword/pattern matching
Text-to-Speech: pyttsx3 with configurable speed and pitch

No unsupported intent guessing. Unknown commands produce:
"I did not understand. Please repeat."
"""

import re
import threading
import time
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np


# ============================================================================
# INTENT CLASSIFICATION
# ============================================================================

class Intent(Enum):
    """Supported user intents (from PRD §3.7)."""
    SURROUNDINGS = "surroundings"     # "What's around me?"
    READ_TEXT = "read_text"           # "Read this", "What does it say?"
    DESCRIBE = "describe"            # "Describe", "What do you see?"
    EMERGENCY = "emergency"          # "Emergency", "Help"
    LOCATION = "location"            # "Where am I?" (Phase 3)
    BATTERY = "battery"              # "Battery status" (Phase 3)
    INTERNET = "internet"            # "Internet status" (Phase 3)
    UNKNOWN = "unknown"


# Intent patterns: list of (regex_pattern, Intent)
# Order matters — first match wins
INTENT_PATTERNS: List[Tuple[str, Intent]] = [
    # Emergency — highest priority
    (r"\b(emergency|help me|help|danger|sos)\b", Intent.EMERGENCY),

    # Surroundings
    (r"\b(around me|surroundings|what'?s around|nearby|around)\b", Intent.SURROUNDINGS),
    (r"\b(what is near|what'?s near)\b", Intent.SURROUNDINGS),

    # Read text / OCR
    (r"\b(read|text|what does it say|ocr|sign|label|board)\b", Intent.READ_TEXT),

    # Describe scene
    (r"\b(describe|scene|what'?s in front|front of me|look|see)\b", Intent.DESCRIBE),
    (r"\b(what is this|what is that|what do you see)\b", Intent.DESCRIBE),

    # Location (Phase 3 placeholder)
    (r"\b(where am i|location|gps|address)\b", Intent.LOCATION),

    # Battery (Phase 3 placeholder)
    (r"\b(battery|power|charge)\b", Intent.BATTERY),

    # Internet (Phase 3 placeholder)
    (r"\b(internet|network|connection|wifi|online)\b", Intent.INTERNET),
]


def classify_intent(text: str) -> Intent:
    """
    Classify user speech into a supported intent.

    Uses rule-based keyword matching. No guessing for unsupported intents.
    If no pattern matches, returns Intent.UNKNOWN.

    Args:
        text: Transcribed speech text

    Returns:
        Classified Intent enum value
    """
    if not text or not text.strip():
        return Intent.UNKNOWN

    text_lower = text.lower().strip()
    # Normalize curly/smart quotes to straight apostrophes for regex matching
    text_lower = text_lower.replace('\u2019', "'").replace('\u2018', "'")

    for pattern, intent in INTENT_PATTERNS:
        if re.search(pattern, text_lower):
            return intent

    return Intent.UNKNOWN


# ============================================================================
# TEXT-TO-SPEECH
# ============================================================================

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[SpeechEngine] WARNING: pyttsx3 not installed. Run: pip install pyttsx3")


class TextToSpeech:
    """
    Text-to-Speech engine using pyttsx3.

    Creates a new engine per utterance in a daemon thread to avoid
    blocking the main loop and to work around pyttsx3 threading
    limitations on Windows.
    """

    def __init__(self, rate: int = 175, volume: float = 1.0):
        """
        Initialize TTS configuration.

        Args:
            rate: Speech rate (words per minute, default 175)
            volume: Volume level 0.0 to 1.0
        """
        self._rate = rate
        self._volume = volume
        self._speaking = False
        self._lock = threading.Lock()

        if TTS_AVAILABLE:
            # Test initialization
            try:
                engine = pyttsx3.init()
                engine.stop()
                print(f"[TTS] ✓ Initialized (rate={rate}, volume={volume})")
            except Exception as e:
                print(f"[TTS] Init test failed: {e}")

    def speak(self, text: str) -> None:
        """
        Speak text asynchronously (non-blocking).

        Creates a daemon thread for each utterance. Only one utterance
        at a time — new calls while speaking are queued.

        Args:
            text: Text to speak
        """
        if not text or not TTS_AVAILABLE:
            return

        # Clean text for speech
        clean_text = self._clean_for_speech(text)
        if not clean_text:
            return

        # Run in daemon thread
        thread = threading.Thread(
            target=self._speak_thread,
            args=(clean_text,),
            daemon=True
        )
        thread.start()

    def speak_sync(self, text: str) -> None:
        """
        Speak text synchronously (blocking).

        Args:
            text: Text to speak
        """
        if not text or not TTS_AVAILABLE:
            return

        clean_text = self._clean_for_speech(text)
        if not clean_text:
            return

        self._speak_thread(clean_text)

    def _speak_thread(self, text: str) -> None:
        """Thread target for speaking."""
        with self._lock:
            try:
                self._speaking = True
                engine = pyttsx3.init()
                engine.setProperty('rate', self._rate)
                engine.setProperty('volume', self._volume)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                print(f"[TTS] Speech error: {e}")
            finally:
                self._speaking = False

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Remove markdown and special characters for natural speech."""
        text = text.replace('*', '').replace('#', '').replace('`', '')
        text = text.replace('"', '').replace('_', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @property
    def is_speaking(self) -> bool:
        """Whether TTS is currently active."""
        return self._speaking

    @property
    def rate(self) -> int:
        """Current speech rate."""
        return self._rate

    @rate.setter
    def rate(self, value: int) -> None:
        """Set speech rate (50-300 WPM)."""
        self._rate = max(50, min(300, value))

    @property
    def volume(self) -> float:
        """Current volume level."""
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set volume (0.0-1.0)."""
        self._volume = max(0.0, min(1.0, value))


# ============================================================================
# SPEECH RECOGNITION (WHISPER)
# ============================================================================

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("[SpeechEngine] WARNING: whisper not installed. Run: pip install openai-whisper")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("[SpeechEngine] WARNING: sounddevice not installed. Run: pip install sounddevice")


class SpeechRecognizer:
    """
    Speech recognition using OpenAI Whisper 'small' model.

    Captures audio from microphone via sounddevice, transcribes with
    Whisper for offline-capable recognition. Target accuracy: 90%+.

    Usage:
        recognizer = SpeechRecognizer()
        text = recognizer.listen()
        intent = classify_intent(text)
    """

    # Whisper model size — 'small' per PRD, good balance of speed/accuracy
    MODEL_SIZE = "small"

    # Audio settings
    SAMPLE_RATE = 16000
    CHANNELS = 1
    RECORD_SECONDS = 5  # Default recording duration

    # Silence detection
    SILENCE_THRESHOLD = 0.01  # RMS threshold for silence
    SILENCE_DURATION = 1.5    # Seconds of silence to stop recording

    def __init__(
        self,
        model_name: str = "base.en",
        device: Optional[str] = None
    ):
        """
        Initialize Whisper model.

        Args:
            model_name: Whisper model size ('tiny', 'base.en', 'small', etc.)
            device: Force device ('cuda', 'cpu', or None for auto)
        """
        self._model = None
        self._device = device
        self._is_listening = False

        if not WHISPER_AVAILABLE:
            print("[SpeechRecognizer] Disabled — whisper not installed")
            return

        if not SOUNDDEVICE_AVAILABLE:
            print("[SpeechRecognizer] Disabled — sounddevice not installed")
            return

        self._load_model(model_name)

    def _load_model(self, model_name: str) -> None:
        """Load the Whisper model."""
        try:
            print(f"[SpeechRecognizer] Loading Whisper '{model_name}' model...")

            # Use requested device or fallback to CPU
            import torch
            if self._device:
                device = self._device
            else:
                device = "cuda" if torch.cuda.is_available() else "cpu"

            self._device = device
            self._model = whisper.load_model(model_name, device=device)
            self._is_available = True
            print(f"[SpeechRecognizer] \u2713 Whisper '{model_name}' loaded on {self._device}")

        except Exception as e:
            print(f"[SpeechRecognizer] \u2717 Failed to load Whisper model: {e}")
            self._is_available = False

    def listen(
        self,
        duration: float = RECORD_SECONDS,
        auto_stop: bool = True,
        callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Listen for speech and transcribe.

        Captures audio from the microphone, then transcribes using Whisper.

        Args:
            duration: Maximum recording duration in seconds
            auto_stop: Stop recording early on extended silence
            callback: Optional function called with "Listening..." status

        Returns:
            Transcribed text string, or empty string on failure
        """
        if self._model is None:
            return ""

        try:
            self._is_listening = True

            if callback:
                callback("Listening...")

            # Record audio
            audio = self._record_audio(duration, auto_stop)

            if audio is None or len(audio) < self.SAMPLE_RATE * 0.3:
                # Too short — likely just noise
                return ""

            if callback:
                callback("Processing speech...")

            # Transcribe with Whisper
            result = self._model.transcribe(
                audio,
                language="en",
                fp16=(self._device == "cuda"),
            )

            text = result.get("text", "").strip()

            if text:
                print(f"[SpeechRecognizer] Heard: \"{text}\"")

            return text

        except Exception as e:
            print(f"[SpeechRecognizer] Listen error: {e}")
            return ""
        finally:
            self._is_listening = False

    def transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """
        Transcribe raw PCM audio data (16kHz, 16-bit mono).

        Args:
            pcm_bytes: Raw audio bytes

        Returns:
            Transcribed text
        """
        if self._model is None:
            return ""

        try:
            # Convert PCM bytes (int16) to float32 numpy array
            audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            result = self._model.transcribe(
                audio_float32,
                language="en",
                fp16=(self._device == "cuda"),
            )
            text = result.get("text", "").strip()
            if text:
                print(f"[SpeechRecognizer] Transcribed: \"{text}\"")
            return text

        except Exception as e:
            print(f"[SpeechRecognizer] Transcription error: {e}")
            return ""

    def _record_audio(
        self,
        duration: float,
        auto_stop: bool
    ) -> Optional[np.ndarray]:
        """
        Record audio from microphone.

        Args:
            duration: Maximum recording seconds
            auto_stop: Stop on prolonged silence

        Returns:
            Audio as float32 numpy array at 16kHz, or None
        """
        try:
            frames = []
            silence_start = None
            has_speech = False

            total_samples = int(self.SAMPLE_RATE * duration)
            chunk_size = int(self.SAMPLE_RATE * 0.1)  # 100ms chunks

            print("[SpeechRecognizer] 🎙️ Recording...")

            for offset in range(0, total_samples, chunk_size):
                remaining = min(chunk_size, total_samples - offset)

                chunk = sd.rec(
                    remaining,
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype=np.float32,
                    blocking=True
                )
                frames.append(chunk.flatten())

                # Check for silence (auto-stop)
                if auto_stop:
                    rms = np.sqrt(np.mean(chunk ** 2))

                    if rms > self.SILENCE_THRESHOLD:
                        has_speech = True
                        silence_start = None
                    elif has_speech:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.SILENCE_DURATION:
                            print("[SpeechRecognizer] Silence detected, stopping.")
                            break

            audio = np.concatenate(frames)
            print(f"[SpeechRecognizer] Recorded {len(audio) / self.SAMPLE_RATE:.1f}s")

            return audio

        except Exception as e:
            print(f"[SpeechRecognizer] Recording error: {e}")
            return None

    def listen_async(
        self,
        duration: float = RECORD_SECONDS,
        callback: Optional[Callable[[str, Intent], None]] = None
    ) -> threading.Thread:
        """
        Listen in a background thread and invoke callback with result.

        Args:
            duration: Max recording duration
            callback: Function(text, intent) called with transcription result

        Returns:
            The background thread
        """
        def _listen_thread():
            text = self.listen(duration=duration)
            intent = classify_intent(text)
            if callback:
                callback(text, intent)

        thread = threading.Thread(target=_listen_thread, daemon=True)
        thread.start()
        return thread

    @property
    def is_available(self) -> bool:
        """Whether speech recognition is ready."""
        return self._model is not None

    @property
    def is_listening(self) -> bool:
        """Whether currently recording/transcribing."""
        return self._is_listening


# ============================================================================
# UNIFIED SPEECH ENGINE
# ============================================================================

class SpeechEngine:
    """
    Unified speech I/O engine combining STT + Intent + TTS.

    Provides a single interface for all voice interaction:
    - listen() → transcribe speech → classify intent
    - speak() → convert text to speech

    Usage:
        engine = SpeechEngine()
        text, intent = engine.listen_and_classify()
        engine.speak("I understood your request.")
    """

    def __init__(
        self,
        whisper_model: str = "small",
        tts_rate: int = 175,
        tts_volume: float = 1.0
    ):
        self.tts = TextToSpeech(rate=tts_rate, volume=tts_volume)
        self.stt = SpeechRecognizer(model_name=whisper_model)

    def speak(self, text: str) -> None:
        """Speak text asynchronously."""
        self.tts.speak(text)

    def speak_sync(self, text: str) -> None:
        """Speak text synchronously (blocking)."""
        self.tts.speak_sync(text)

    def listen_and_classify(
        self,
        duration: float = 5.0
    ) -> Tuple[str, Intent]:
        """
        Listen for speech, transcribe, and classify intent.

        Args:
            duration: Max recording duration

        Returns:
            Tuple of (transcribed_text, classified_intent)
        """
        text = self.stt.listen(duration=duration)
        intent = classify_intent(text)
        return text, intent

    @property
    def is_available(self) -> bool:
        """Whether both STT and TTS are available."""
        return self.stt.is_available


# Quick test when run directly
if __name__ == "__main__":
    print("SpeechEngine Module Test")
    print("=" * 40)

    # Test intent classification
    print("\n--- Intent Classification ---")
    test_phrases = [
        "What's around me?",
        "Read this text",
        "Describe the scene",
        "Emergency!",
        "Where am I?",
        "How's the battery?",
        "Is internet working?",
        "Play some music",  # Unknown
        "Tell me what you see",
        "Help me please",
        "",  # Empty
    ]

    for phrase in test_phrases:
        intent = classify_intent(phrase)
        print(f"  \"{phrase}\" → {intent.value}")

    # Test TTS
    print("\n--- Text-to-Speech ---")
    tts = TextToSpeech()
    tts.speak("AIVA speech engine test. System ready.")
    time.sleep(3)

    # Test full engine (if mic available)
    print("\n--- Full SpeechEngine ---")
    engine = SpeechEngine()
    if engine.is_available:
        engine.speak("Say something to test speech recognition.")
        time.sleep(2)
        text, intent = engine.listen_and_classify()
        print(f"\n  You said: \"{text}\"")
        print(f"  Intent: {intent.value}")
    else:
        print("  Speech recognition not available (missing whisper or sounddevice)")
