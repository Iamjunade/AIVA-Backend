"""
AIVA Server — WebSocket Server
=================================
Production-grade async WebSocket server for AIVA client-server communication.

Binds to 0.0.0.0:8765 (configurable via AIVA_PORT).
Accepts binary frame messages from mobile clients, routes them through
the vision pipeline (FrameProcessor), and returns structured JSON responses.

Security:
    - Bearer token authentication on connection
    - Per-client rate limiting (max 30 fps)
    - No raw frame storage (GDPR compliance)
    - Max 2 concurrent connections (resource protection)

Usage:
    python -m server.aiva_server

    Or from project root:
    python server/aiva_server.py
"""

import asyncio
import json
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Set

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import websockets
    from websockets.asyncio.server import ServerConnection
except ImportError:
    print("[AIVA Server] FATAL: websockets not installed. Run: pip install websockets")
    sys.exit(1)

from server.config import (
    SERVER_HOST,
    SERVER_PORT,
    MAX_CLIENTS,
    PROCESSING_TIMEOUT_MS,
    LOG_LEVEL,
)
from server.auth import Authenticator, RateLimiter, AuthError, RateLimitError
from server.protocol import (
    FrameRequest,
    FrameResponse,
    ErrorResponse,
    ConnectedResponse,
    ErrorCode,
    MessageType,
    HEADER_SIZE,
    CommandResponse,
    SpeechResponse,
)
from server.frame_processor import FrameProcessor
from server.intent_classifier import IntentClassifier, Intent
from server.memory_engine import ContinuousMemoryEngine
from src.speech_engine import SpeechEngine


# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aiva.server")


# =============================================================================
# SERVER
# =============================================================================

class AIVAServer:
    """
    Async WebSocket server for AIVA.

    Manages connections, authentication, rate limiting, and frame processing.

    Lifecycle:
        1. Server starts, loads all AI models (FrameProcessor)
        2. Client connects with bearer token
        3. Server authenticates and sends "connected" response
        4. Client sends binary frame messages
        5. Server processes frames and returns JSON
        6. Server handles graceful shutdown on SIGINT/SIGTERM
    """

    def __init__(self):
        self._auth = Authenticator()
        self._rate_limiter = RateLimiter()
        self._processor: FrameProcessor = None  # Lazy init
        self._speech_engine: SpeechEngine = None # Lazy init
        self._intent_classifier: IntentClassifier = None
        self._memory_engine: ContinuousMemoryEngine = None
        self._active_clients: Set[str] = set()
        self._client_count = 0
        self._total_frames_processed = 0
        self._shutdown_event = asyncio.Event()
        self._listening_thread = None
        self._is_listening = False

    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info("=" * 60)
        logger.info("AIVA Server Starting")
        logger.info("=" * 60)

        # Load AI models (blocking — runs once at startup)
        logger.info("Loading AI models...")
        self._processor = FrameProcessor()
        self._speech_engine = SpeechEngine()
        self._intent_classifier = IntentClassifier()
        self._memory_engine = ContinuousMemoryEngine(
            sample_interval_sec=4.0,
            on_face_learned=self._on_face_learned
        )
        self._memory_engine.start()

        if not self._processor.is_ready:
            logger.error("Critical models failed to load. Server cannot start.")
            return

        models = self._processor.models_status
        logger.info(f"Models: {json.dumps(models)}")
        logger.info(f"Speech Engine: {'Ready' if self._speech_engine.is_available else 'Mic/Speaker Unavailable (Server Mode)'}")

        # The server now acts purely as a WebSocket backend. 
        # The laptop microphone continuous listening loop has been disabled.
        # Mobile applications are expected to stream audio to the FRAME_AUDIO endpoint.

        # Start WebSocket server
        logger.info(f"Binding to ws://{SERVER_HOST}:{SERVER_PORT}")
        logger.info(f"Max clients: {MAX_CLIENTS}")
        logger.info(f"Rate limit: {self._rate_limiter.max_fps} fps/client")
        logger.info(f"Processing timeout: {PROCESSING_TIMEOUT_MS}ms")
        logger.info("-" * 60)

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                pass

        try:
            async with websockets.serve(
                self._handle_connection,
                SERVER_HOST,
                SERVER_PORT,
                max_size=2 * 1024 * 1024,  # 2MB max message (JPEG frames)
                ping_interval=20,
                ping_timeout=20,     # Tolerant of ADB tunnel latency
                close_timeout=5,     # Graceful close timeout
                process_request=self._process_request,
            ):
                logger.info(f"Server ready at ws://{SERVER_HOST}:{SERVER_PORT}")
                await self._shutdown_event.wait()
        except OSError as e:
            logger.error(f"Failed to bind: {e}")
            raise

    def _signal_handler(self) -> None:
        """Handle shutdown signal."""
        logger.info("Shutdown signal received")
        self._is_listening = False
        if self._memory_engine:
            self._memory_engine.stop()
        self._shutdown_event.set()

    def _on_face_learned(self, name: str) -> str:
        """Callback from memory_engine to reload face models when a new person is registered."""
        if self._processor and self._processor._face_detector:
            self._processor._face_detector.load_known_faces()
            return f"Successfully saved {name} and hot-reloaded the local face database."
        return f"Saved {name} but could not hot-reload the face database."

    def _continuous_listen_loop(self):
        """Runs in a background thread, constantly listening to the laptop mic."""
        # Create a new event loop for this thread to handle async calls if needed, 
        # though we will use thread-safe calls to the memory engine.
        while self._is_listening:
            try:
                # listen() blocks until it hears something and silence follows
                text = self._speech_engine.stt.listen(duration=7.0)
                if text and self._memory_engine:
                    text_lower = text.lower()
                    
                    # Optional: Add a wake word check here if it triggers too often on background noise
                    # "aiva" or just answer any direct question
                    
                    # To avoid answering TV noise, we only respond if it sounds like a question
                    # or contains our name.
                    is_question = any(q in text_lower for q in ['what', 'where', 'who', 'how', 'is there', 'are there', 'can you', 'aiva'])
                    if is_question or len(text) > 15:
                        logger.info(f"[Hands-Free Mic] Heard: '{text}'")
                        logger.info("[Hands-Free] Asking Continuous Memory...")
                        answer = self._memory_engine.ask_memory(text)
                        logger.info(f"[Hands-Free] AIVA Answer: {answer}")
                        self._speech_engine.speak_sync(answer)
            except Exception as e:
                logger.error(f"[Hands-Free Mic] Loop Error: {e}")
                time.sleep(1.0)

    async def _process_request(self, connection, request):
        """
        Intercept HTTP requests before WebSocket handshake.
        Handles JWT issuance at POST /auth/token.
        """
        path = request.path
        if path == "/auth/token" and request.method == "POST":
            # 1. Check for legacy AUTH_TOKEN as "Master Key" in headers
            #    (Authorization: Bearer <AUTH_TOKEN>)
            #    In production, this would validate user credentials (DB lookup)
            from server.config import AUTH_TOKEN, AUTH_MODE
            
            # Extract header
            auth_header = request.headers.get("Authorization", "")
            token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header
            
            if not token or token != AUTH_TOKEN:
                 return (
                    401,
                    [("Content-Type", "application/json")],
                    json.dumps({"error": "Invalid master token"}).encode("utf-8")
                )

            # 2. Generate new JWT
            client_id = f"client-{int(time.time())}"
            # Attempt to use JWT manager (only available if AUTH_MODE=jwt)
            if self._auth.mode == "jwt" and self._auth.jwt_manager:
                new_token = self._auth.jwt_manager.generate_token(client_id)
                expiry = self._auth.jwt_manager._expiry_hours * 3600
                return (
                    200,
                    [("Content-Type", "application/json")],
                    json.dumps({
                        "access_token": new_token,
                        "token_type": "Bearer",
                        "expires_in": expiry
                    }).encode("utf-8")
                )
            else:
                 return (
                    400,
                    [("Content-Type", "application/json")],
                    json.dumps({"error": "Server not in JWT mode"}).encode("utf-8")
                )
        
        # 3. Handle /auth/refresh (POST)
        if path == "/auth/refresh" and request.method == "POST":
            auth_header = request.headers.get("Authorization", "")
            token = auth_header[7:] if auth_header.startswith("Bearer ") else auth_header
            
            if self._auth.mode == "jwt" and self._auth.jwt_manager:
                try:
                    new_token = self._auth.jwt_manager.refresh_token(token)
                    expiry = self._auth.jwt_manager._expiry_hours * 3600
                    return (
                        200,
                        [("Content-Type", "application/json")],
                        json.dumps({
                            "access_token": new_token,
                            "token_type": "Bearer",
                            "expires_in": expiry
                        }).encode("utf-8")
                    )
                except AuthError as e:
                     return (
                        401,
                        [("Content-Type", "application/json")],
                        json.dumps({"error": str(e)}).encode("utf-8")
                    )
            else:
                 return (
                    400,
                    [("Content-Type", "application/json")],
                    json.dumps({"error": "Server not in JWT mode"}).encode("utf-8")
                )

        # Allow normal WebSocket handshake for other paths
        return None

    async def _handle_connection(self, websocket) -> None:
        """
        Handle a single WebSocket connection lifecycle.
        Steps:
            1. Check connection limit
            2. Authenticate via bearer token (Static or JWT)
            3. Send "connected" response
            4. Enter message loop
            5. Clean up on disconnect
        """
        # Note: websockets 10.x+ passes ServerConnection as first arg
        # We handle both `start` and `serve` usage
        
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"

        # --- Connection limit check ---
        if len(self._active_clients) >= MAX_CLIENTS:
            error = ErrorResponse(
                code=ErrorCode.SERVER_OVERLOADED,
                message=f"Server full: {MAX_CLIENTS} clients connected"
            )
            await websocket.send(json.dumps(error.to_dict()))
            await websocket.close()
            logger.warning(f"Rejected {client_id}: server full")
            return

        # --- Authentication ---
        try:
            # Extract token from request headers
            request_headers = websocket.request.headers
            token = self._auth.extract_token(request_headers)
            self._auth.validate_token(token)
            
            # If JWT, update client_id from token claim
            if self._auth.mode == "jwt":
                client_id = self._auth.get_client_id(token)

        except AuthError as e:
            error = ErrorResponse(
                code=ErrorCode.AUTH_FAILED,
                message=str(e)
            )
            await websocket.send(json.dumps(error.to_dict()))
            await websocket.close()
            logger.warning(f"Auth failed for {client_id}: {e}")
            return

        # --- Connection accepted ---
        self._active_clients.add(client_id)
        self._client_count += 1
        logger.info(f"Client connected: {client_id} (total: {len(self._active_clients)})")

        # Send connected response
        connected = ConnectedResponse(
            models_loaded=self._processor.is_ready,
        )
        await websocket.send(json.dumps(connected.to_dict()))

        # --- Message loop ---
        try:
            async for message in websocket:
                await self._handle_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client disconnected: {client_id} (code={e.code})")
        except Exception as e:
            logger.error(f"Connection error for {client_id}: {e}")
        finally:
            self._active_clients.discard(client_id)
            self._rate_limiter.remove_client(client_id)
            logger.info(
                f"Client removed: {client_id} "
                f"(remaining: {len(self._active_clients)})"
            )

    async def _handle_message(
        self,
        websocket: ServerConnection,
        message: bytes,
        client_id: str,
    ) -> None:
        """
        Handle a single incoming WebSocket message.

        Args:
            websocket: Client connection
            message: Raw binary message
            client_id: Client identifier for rate limiting
        """
        # Must be binary (not text)
        if isinstance(message, str):
            if message.startswith("TEST_ASK:"):
                text = message[9:]
                logger.info(f"Test Ask: '{text}'")
                if self._memory_engine:
                    loop = asyncio.get_event_loop()
                    answer = await loop.run_in_executor(None, self._memory_engine.ask_memory, text)
                    await websocket.send(json.dumps({"type": "test_answer", "answer": answer}))
                return
                
            error = ErrorResponse(
                code=ErrorCode.INVALID_MESSAGE,
                message="Expected binary frame, got text"
            )
            await websocket.send(json.dumps(error.to_dict()))
            return

        # --- Rate limiting ---
        try:
            self._rate_limiter.check(client_id)
        except RateLimitError as e:
            error = ErrorResponse(
                code=ErrorCode.RATE_LIMITED,
                message=str(e)
            )
            await websocket.send(json.dumps(error.to_dict()))
            return

        # --- Parse request ---
        try:
            request = FrameRequest.from_bytes(message)
        except ValueError as e:
            error = ErrorResponse(
                code=ErrorCode.INVALID_MESSAGE,
                message=str(e)
            )
            await websocket.send(json.dumps(error.to_dict()))
            return

        # --- Handle PING ---
        if request.msg_type == MessageType.PING:
            pong = {"type": "pong", "timestamp_ms": int(time.time() * 1000)}
            await websocket.send(json.dumps(pong))
            return

        # --- Handle AUDIO (Voice Command) ---
        if request.msg_type == MessageType.FRAME_AUDIO:
            try:
                loop = asyncio.get_event_loop()
                # Transcribe in thread (Whisper is CPU intensive)
                text = await loop.run_in_executor(
                    None,
                    self._speech_engine.stt.transcribe_pcm,
                    request.payload_bytes
                )
                
                # Classify Intent
                intent = self._intent_classifier.classify(text)
                
                # Execute Command
                if intent == Intent.EMERGENCY:
                    logger.warning(f"!!! EMERGENCY INTENT DETECTED from {client_id} !!!")
                    cmd = CommandResponse(action="SOS")
                    await websocket.send(json.dumps(cmd.to_dict()))
                    
                elif intent == Intent.LOCATION:
                    logger.info(f"Location request from {client_id}")
                    cmd = CommandResponse(action="LOCATION")
                    await websocket.send(json.dumps(cmd.to_dict()))
                
                else:
                    # Route all other inquiries to the continuous memory!
                    if self._memory_engine:
                        logger.info(f"Asking Continuous Memory: '{text}'")
                        answer = await loop.run_in_executor(
                            None,
                            self._memory_engine.ask_memory,
                            text
                        )
                        logger.info(f"AIVA Answer: {answer}")
                        
                        # Send the textual response back to the client to be spoken natively
                        speech_pkt = SpeechResponse(text=answer)
                        await websocket.send(json.dumps(speech_pkt.to_dict()))
                
                return

            except Exception as e:
                logger.error(f"Audio processing error: {e}")
                err = ErrorResponse(code=ErrorCode.SERVER_OVERLOADED, message="Voice processing failed")
                await websocket.send(json.dumps(err.to_dict()))
                return

        # --- Process VISION frame (blocking inference) ---
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._processor.process,
                    request.payload_bytes,  # Updated from jpeg_bytes
                    request.msg_type,
                    request.frame_id,
                ),
                timeout=PROCESSING_TIMEOUT_MS / 1000.0,
            )

            self._total_frames_processed += 1
            
            # --- PHASE 2: SEMANTIC MEMORY & PROACTIVE HAZARDS ---
            semantic_text = ""
            critical_hazard = ""
            
            if response.detections:
                dets = [f"{d['class']} at {d.get('distance_m', 0):.1f}m" for d in response.detections]
                semantic_text = f"Visible objects: {', '.join(dets)}."
                
            if response.warnings:
                warns = []
                for w in response.warnings:
                    warns.append(w['message'])
                    # Trigger on critical dangers (using the engine's built-in is_critical flag)
                    if w.get('is_critical', False):
                        critical_hazard = w['message']
                semantic_text += f" Warnings: {', '.join(warns)}."

            if response.faces:
                semantic_text += f" Recognized People: {', '.join(response.faces)}."

            if response.unknown_faces_count > 0:
                semantic_text += f" [Unknown Person Detected: {response.unknown_faces_count} unknown faces are in the frame right now.]"

            # Inject semantic text into memory engine
            if self._memory_engine:
                self._memory_engine.update_latest_frame(request.payload_bytes, semantic_text)
                
            # Proactively speak out critical hazards if speech engine is available
            # The Android app natively intercepts the `warnings` list and plays Text-to-Speech
            # directly out of the phone speaker, making the following legacy code obsolete.
            # (Legacy server speaker code removed)

        except asyncio.TimeoutError:
            error = ErrorResponse(
                frame_id=request.frame_id,
                code=ErrorCode.INFERENCE_TIMEOUT,
                message=f"Processing exceeded {PROCESSING_TIMEOUT_MS}ms"
            )
            await websocket.send(json.dumps(error.to_dict()))
            logger.warning(f"Timeout on frame {request.frame_id} from {client_id}")
            return

        except Exception as e:
            error = ErrorResponse(
                frame_id=request.frame_id,
                code=ErrorCode.MODEL_UNAVAILABLE,
                message=f"Processing error: {str(e)}"
            )
            await websocket.send(json.dumps(error.to_dict()))
            logger.error(f"Processing error: {e}")
            return

        # --- Send response ---
        response_json = json.dumps(response.to_dict())
        await websocket.send(response_json)

    # =========================================================================
    # STATUS
    # =========================================================================

    @property
    def stats(self) -> Dict:
        """Server statistics."""
        return {
            "active_clients": len(self._active_clients),
            "total_frames": self._total_frames_processed,
        }


# =============================================================================
# ENTRY POINT
# =============================================================================

async def main():
    """Start the AIVA server."""
    server = AIVAServer()
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)
