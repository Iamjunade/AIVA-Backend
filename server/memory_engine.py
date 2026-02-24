"""
AIVA Server — Continuous Memory Engine
========================================
Maintains a persistent visual memory of the user's environment.
Runs a background thread to sample live frames every N seconds and
inject them into a persistent Gemini ChatSession.
"""

import threading
import time
import os
import cv2
import numpy as np

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[MemoryEngine] WARNING: Pillow not installed.")

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[MemoryEngine] WARNING: google-generativeai not installed.")

from dotenv import load_dotenv
from pathlib import Path

class ContinuousMemoryEngine:
    """
    Novel architecture: maintains a true conversational memory of the visual
    environment over time using Gemini 2.0 Flash's massive context window.
    """
    def __init__(self, sample_interval_sec: float = 4.0, on_face_learned=None):
        self._sample_interval = sample_interval_sec
        self._on_face_learned = on_face_learned
        self._latest_frame_bytes = None
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._latest_semantic_context = ""
        
        self._model = None
        self._chat = None
        
        self._initialize_genai()

    def _initialize_genai(self):
        """Load API key and configure Gemini."""
        if not GENAI_AVAILABLE or not PIL_AVAILABLE:
            print("[MemoryEngine] ✗ Required libraries missing.")
            return

        # Try to load .env
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            print("[MemoryEngine] ✗ Gemini API key not found in environment.")
            return

        try:
            genai.configure(api_key=api_key)
            
            def save_person_face(name: str) -> str:
                """Saves the last seen unknown person's face to the local database so AIVA can recognize them in the future."""
                print(f"[MemoryEngine] Executing Agent Tool: save_person_face('{name}')")
                if not self._latest_frame_bytes:
                    return f"Failed: No recent camera frame available to save {name}."
                
                try:
                    # Parse image from bytes
                    arr = np.frombuffer(self._latest_frame_bytes, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    
                    # Ensure known_faces directory exists
                    os.makedirs("known_faces", exist_ok=True)
                    
                    # Sanitize name for filename
                    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c=='_']).rstrip()
                    file_path = f"known_faces/{safe_name.lower()}.jpg"
                    
                    # Save image
                    cv2.imwrite(file_path, frame)
                    print(f"[MemoryEngine] Saved {name}'s face to {file_path}")
                    
                    # Trigger callback to reload detector
                    msg = f"Saved {name}'s face successfully."
                    if self._on_face_learned:
                        msg = self._on_face_learned(name)
                    return msg
                except Exception as e:
                    return f"Failed to save {name}'s face: {e}"

            system_instruction = (
                "You are AIVA, an AI Vision Assistant for a blind user. "
                "You receive a continuous stream of camera frames combined with "
                "real-time sensory data about detected objects, faces, and proximity hazards. "
                "Your job is to act as the user's continuous spatial memory and conversational guide.\n\n"
                "CRITICAL RULES:\n"
                "1. BE EXTREMELY BRIEF and natural. Your answers are spoken aloud. Never use markdown, bullet points, or complex formatting.\n"
                "2. Keep responses to 1-2 short sentences maximum. The user cannot wait for long paragraphs.\n"
                "3. If the user asks what is around them, use the recent sensory data to give a quick, prioritized summary (e.g., 'There's a chair 1 meter ahead and a person to your left.').\n"
                "4. If the user asks about a past event, use your conversation history to recall it.\n"
                "5. If a new face is detected, the pipeline will say 'Unknown Person Detected.' Use the save_person_face tool to learn them if the user asks.\n"
            )
            
            self._model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_instruction,
                tools=[save_person_face]
            )
            self._chat = self._model.start_chat(history=[])
            print(f"[MemoryEngine] ✓ Initialized Gemini ChatSession (Interval {self._sample_interval}s)")
        except Exception as e:
            print(f"[MemoryEngine] ✗ Failed to initialize: {e}")

    def update_latest_frame(self, frame_bytes: bytes, semantic_context: str = "") -> None:
        """Called constantly by the WebSocket server to provide the latest frame and local AI text."""
        with self._lock:
            self._latest_frame_bytes = frame_bytes
            if semantic_context:
                self._latest_semantic_context = semantic_context

    def start(self):
        """Start the background sampling loop."""
        if not self._chat:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._memory_loop, daemon=True)
        self._thread.start()
        print("[MemoryEngine] ✓ Background memory loop started.")

    def stop(self):
        """Stop the background sampling loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _prepare_image(self, jpeg_bytes: bytes):
        """Convert JPEG bytes to PIL Image, resize for speed."""
        try:
            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                return None
                
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame)
            
            # Resize
            max_size = 512
            if max(pil_img.size) > max_size:
                ratio = max_size / max(pil_img.size)
                new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)
                
            return pil_img
        except Exception as e:
            print(f"[MemoryEngine] Image prepare error: {e}")
            return None

    def _memory_loop(self):
        """Background thread that samples frames and sends to Gemini."""
        while self._running:
            start_time = time.time()
            
            semantic_text = ""
            with self._lock:
                frame_bytes = self._latest_frame_bytes
                semantic_text = self._latest_semantic_context
                # Keep latest frame available so we can re-sample if video frozen?
                # Actually, better to clear it, so we don't spam the exact same image 
                # if the user turns off the camera stream.
                self._latest_frame_bytes = None
                self._latest_semantic_context = ""
                
            if frame_bytes:
                pil_img = self._prepare_image(frame_bytes)
                if pil_img:
                    try:
                        timestamp = time.strftime("%H:%M:%S")
                        msg = f"[SYSTEM: Time is {timestamp}. This is the current camera view. "
                        if semantic_text:
                            msg += f"Local AI sensors report the following at this exact moment: {semantic_text}. "
                        msg += "Do not reply, just remember it for context.]"
                        self._chat.send_message([msg, pil_img])
                    except Exception as e:
                        print(f"[MemoryEngine] Error sending frame to memory: {e}")

            elapsed = time.time() - start_time
            sleep_time = max(0.1, self._sample_interval - elapsed)
            time.sleep(sleep_time)

    def ask_memory(self, question: str) -> str:
        """Ask a question about the current or past context."""
        if not self._chat:
            return "My visual memory is currently disabled."
            
        try:
            print(f"[MemoryEngine] Querying memory: '{question}'")
            # First, check if there's an immediate latest frame to send WITH the question
            # This ensures the very latest data is evaluated for immediate questions.
            semantic_text = ""
            with self._lock:
                frame_bytes = self._latest_frame_bytes
                semantic_text = self._latest_semantic_context
                self._latest_frame_bytes = None
                self._latest_semantic_context = ""
                
            content = [question]
            if frame_bytes:
                pil_img = self._prepare_image(frame_bytes)
                if pil_img:
                    content.append(pil_img)
                    sys_msg = "[SYSTEM: This is the very latest camera view corresponding to the user's question. "
                    if semantic_text:
                        sys_msg += f"Local AI sensors currently report: {semantic_text}."
                    sys_msg += "]"
                    content.append(sys_msg)

            response = self._chat.send_message(content)
            return response.text.strip()
        except Exception as e:
            print(f"[MemoryEngine] Query error: {e}")
            return "I had trouble accessing my visual memory."
