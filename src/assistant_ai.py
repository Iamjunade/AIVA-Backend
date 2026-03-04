"""
AIVA - Assistant AI Module
===========================
Cloud-based vision AI using Google Gemini API for scene description and OCR.

IMPORTANT: This module is TRIGGER-BASED only. Never call ask_gemini() in a loop.
Each API call has latency (~1-3 seconds) and costs money.

Anti-Hallucination Rules (PRD §10):
- No assumption-based descriptions
- No speculative interpretation
- Only describe what is clearly visible
- Read exact text as captured (no summarization unless requested)
"""

import os
import io
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[AssistantAI] WARNING: Pillow not installed. Run: pip install Pillow")

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[AssistantAI] WARNING: google-generativeai not installed. Run: pip install google-generativeai")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[AssistantAI] WARNING: pyttsx3 not installed. Run: pip install pyttsx3")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("[AssistantAI] WARNING: python-dotenv not installed. Run: pip install python-dotenv")


class AssistantAI:
    """
    Cloud-based vision assistant using Google Gemini API.
    
    Provides scene description, text reading (OCR), and visual question
    answering for visually impaired users. All API calls are trigger-based.
    
    Anti-Hallucination Constraints:
    - Only describe detected/visible content
    - No speculative interpretation
    - Read exact text — no summarization unless explicitly requested
    - If uncertain, say so honestly
    """
    
    # System prompt with strict anti-hallucination rules
    SYSTEM_PROMPT = """You are AIVA, an AI Vision Assistant for a blind person.

CRITICAL RULES:
- ONLY describe what you can clearly see. Never guess or assume.
- Be CONCISE: maximum 2 sentences, each under 15 words.
- Be SAFETY-FIRST: warn about obstacles, stairs, traffic, vehicles.
- If the image is blurry, dark, or unclear, say "The image is unclear." Do NOT guess.
- Do NOT use filler phrases like "I can see", "It appears that", "It looks like".
- Do NOT generate imaginary or speculative descriptions.
- Do NOT describe objects you are less than 80% confident about.

For scene descriptions:
- Start with what's directly in front of the user
- Mention people, obstacles, or important objects
- Include spatial info (left, right, ahead, close, far)

For text reading (OCR):
- Read text EXACTLY as captured — do not paraphrase
- If text is blurry or unclear, say so honestly
- Do NOT summarize unless explicitly asked

For safety:
- Always mention vehicles, stairs, or moving hazards first
- Warn about obstacles in the path"""

    # Model configuration (Google Gemini)
    # Using gemini-2.0-flash for speed (flash-lite can be slower)
    MODEL_NAME = "gemini-2.0-flash"
    
    def __init__(self, env_path: Optional[str] = None):
        """Initialize the assistant."""
        self._model = None
        self._api_key_loaded = False
        self._tts_engine = None
        
        # Initialize text-to-speech
        if TTS_AVAILABLE:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty('rate', 175)  # Speed
                self._tts_engine.setProperty('volume', 1.0)
                print("[AssistantAI] ✓ Text-to-speech initialized")
            except Exception as e:
                print(f"[AssistantAI] TTS init failed: {e}")
        
        if not GENAI_AVAILABLE:
            print("[AssistantAI] AI disabled - google-generativeai library not available")
            return
            
        if not PIL_AVAILABLE:
            print("[AssistantAI] AI disabled - Pillow not available")
            return
        
        self._load_api_key(env_path)
        
        if self._api_key_loaded:
            self._initialize_client()
    
    def _load_api_key(self, env_path: Optional[str] = None) -> bool:
        """Load the API key from .env file."""
        if DOTENV_AVAILABLE:
            search_paths = []
            if env_path:
                search_paths.append(Path(env_path))
            
            search_paths.extend([
                Path.cwd() / ".env",
                Path.cwd().parent / ".env",
                Path(__file__).parent.parent / ".env",
            ])
            
            for path in search_paths:
                if path.exists():
                    load_dotenv(path)
                    break
        
        # Load GOOGLE_API_KEY
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        
        if not self.api_key or self.api_key == "your_api_key_here":
            print("[AssistantAI] ✗ No API key found!")
            print("  Add GOOGLE_API_KEY to your .env file")
            return False
        
        self._api_key_loaded = True
        print("[AssistantAI] ✓ API key loaded")
        return True
    
    def _initialize_client(self) -> None:
        """Initialize the Google Gemini client."""
        try:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=self.SYSTEM_PROMPT
            )
            print(f"[AssistantAI] ✓ Client initialized (Model: {self.MODEL_NAME})")
        except Exception as e:
            print(f"[AssistantAI] ✗ Failed to initialize client: {e}")
            self._model = None
    
    def _prepare_image(self, image: Union[np.ndarray, Image.Image]) -> Image.Image:
        """Convert image to PIL Image for Gemini API."""
        if isinstance(image, np.ndarray):
            # Convert BGR to RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(image)
        else:
            pil_img = image
            
        # Resize aggressively for faster upload (smaller = faster API response)
        max_size = 512  # Reduced from 1024 for speed
        if max(pil_img.size) > max_size:
            ratio = max_size / max(pil_img.size)
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
            
        return pil_img
    
    # TTS is now handled by src/speech_engine.py TextToSpeech class.
    # Left as a thin wrapper for backward compatibility.
    def speak(self, text: str) -> None:
        """Speak text via TTS. Delegates to speech_engine if available."""
        if not text:
            return
        
        # Try speech engine first (new AIVA architecture)
        try:
            from src.speech_engine import TextToSpeech
            tts = TextToSpeech(rate=175)
            tts.speak(text)
            return
        except ImportError:
            pass
        
        # Legacy fallback
        if self._tts_engine:
            import threading
            def _speak_thread(engine, message):
                try:
                    clean_text = message.replace('*', '').replace('#', '').replace('"', '').strip()
                    engine.say(clean_text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"[TTS] Error: {e}")
            try:
                thread_engine = pyttsx3.init()
                thread_engine.setProperty('rate', 175)
                thread_engine.setProperty('volume', 1.0)
                t = threading.Thread(target=_speak_thread, args=(thread_engine, text), daemon=True)
                t.start()
            except Exception as e:
                print(f"[TTS] Failed: {e}")
    
    def ask_gemini(self, image: Union[np.ndarray, Image.Image], prompt: str) -> str:
        """
        Send an image and prompt to Google Gemini and get a response.
        """
        if not self._model:
            return "I'm sorry, the vision system is not available right now."
        
        try:
            pil_image = self._prepare_image(image)
            
            response = self._model.generate_content(
                [prompt, pil_image],
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=300,
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "I couldn't analyze that image. Please try again."
                
        except Exception as e:
            error_msg = str(e)
            
            # Helper to check for common errors without spamming
            is_quota = "quota" in error_msg.lower() or "429" in error_msg
            is_key = "key" in error_msg.lower() or "401" in error_msg or "invalid" in error_msg.lower()
            
            if is_quota:
                print(f"[AssistantAI] Limit reached (429). User needs to wait.")
                return "I'm tired right now. Please ask me again in a minute."
            elif is_key:
                print(f"[AssistantAI] API Key issue: {error_msg[:100]}")
                return "There's a problem with my API key. Please check the configuration."
            else:
                # Show the REAL error for debugging
                error_prefix = error_msg[:150]
                print(f"[AssistantAI] Error: {error_prefix}") 
                return "System error. Check console."
    
    def describe_scene(self, image: Union[np.ndarray, Image.Image]) -> str:
        """Get a concise, factual description of what's visible."""
        return self.ask_gemini(
            image,
            "What is in front of me? Describe only what you can clearly see. "
            "Mention any safety hazards first. Be concise (1-2 sentences)."
        )
    
    def read_text(self, image: Union[np.ndarray, Image.Image]) -> str:
        """Read and return any visible text exactly as captured."""
        return self.ask_gemini(
            image,
            "Read ALL the text visible in this image EXACTLY as written. "
            "Do not paraphrase or summarize. If there is no text, say 'No text visible.'"
        )
    
    def read_specific(self, image: Union[np.ndarray, Image.Image], target: str) -> str:
        """Read specific text (medicine label, bus number, sign)."""
        return self.ask_gemini(
            image,
            f"Look for and read the {target} in this image. "
            f"Read it exactly as written. If not visible, say so."
        )
    
    def answer_question(self, image: Union[np.ndarray, Image.Image], question: str) -> str:
        """Answer a specific question about the image."""
        return self.ask_gemini(image, question)
    
    @property
    def is_available(self) -> bool:
        """Whether the assistant is ready to use."""
        return self._model is not None


# Quick test when run directly
if __name__ == "__main__":
    import sys
    import time
    from src.video_stream import VideoGet
    
    print("AssistantAI Module Test (Google Gemini API)")
    print("=" * 50)
    
    # IP Webcam URL - UPDATE THIS
    VIDEO_SOURCE = 0 # Default to laptop for testing
    
    assistant = AssistantAI()
    
    if not assistant.is_available:
        print("\nAssistant not available. Check your .env file.")
        sys.exit(1)
    
    print(f"\nConnecting to video source: {VIDEO_SOURCE}")
    
    video = VideoGet(src=VIDEO_SOURCE).start()
    
    # Wait for connection
    print("Waiting for video stream...")
    start_time = time.time()
    while video.read() is None:
        if time.time() - start_time > 10:
            print("Timeout!")
            video.stop()
            sys.exit(1)
        time.sleep(0.1)
    
    print("✓ Connected!")
    print("\nPress 'q' to capture and describe the scene")
    print("Press 'r' to capture and read text")
    print("Press ESC to exit\n")
    
    try:
        while True:
            frame = video.read()
            if frame is None:
                continue
            
            preview = frame.copy()
            cv2.putText(preview, "'q' describe | 'r' read text | ESC exit",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("VASIS - AssistantAI Test", preview)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                print("[Analyzing scene...]")
                response = assistant.describe_scene(frame)
                print(f"\n🔊 {response}\n")
                
            elif key == ord('r'):
                print("[Reading text...]")
                response = assistant.read_text(frame)
                print(f"\n📖 {response}\n")
                
            elif key == 27:  # ESC
                break
    finally:
        video.stop()
        cv2.destroyAllWindows()
        print("Test complete!")
