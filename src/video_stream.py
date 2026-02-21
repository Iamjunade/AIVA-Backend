"""
VASIS - Video Stream Module
===========================
Threaded video capture for low-latency frame acquisition from IP Webcam.

The VideoGet class runs a daemon thread that continuously grabs frames,
storing only the latest frame to prevent latency buildup from processing delays.
"""

import threading
import time
from typing import Optional, Tuple

import cv2
import numpy as np


class VideoGet:
    """
    Threaded video frame grabber that maintains only the latest frame.
    
    This class solves the "latency buildup" problem: if frame reading happens
    in the main loop, slow image processing causes the read buffer to fill up,
    creating a 5+ second video delay. By reading frames in a separate thread,
    we always have access to the most recent frame.
    
    Usage:
        video = VideoGet(src="http://192.168.1.5:8080/video").start()
        while True:
            frame = video.read()
            if frame is not None:
                cv2.imshow("Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        video.stop()
    """
    
    def __init__(self, src: str, reconnect_delay: float = 2.0):
        """
        Initialize the video stream.
        
        Args:
            src: Video source URL (IP Webcam) or device index (0 for webcam)
            reconnect_delay: Seconds to wait before reconnection attempt
        """
        self.src = src
        self.reconnect_delay = reconnect_delay
        
        # Thread control
        self._stopped = False
        self._lock = threading.Lock()
        
        # Frame buffer - stores only the latest frame
        self._frame: Optional[np.ndarray] = None
        self._grabbed: bool = False
        
        # Connection state
        self._connected: bool = False
        self._stream: Optional[cv2.VideoCapture] = None
        
        # Stats
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._last_fps_time: float = time.time()
    
    def start(self) -> "VideoGet":
        """
        Start the frame grabbing thread.
        
        Returns:
            Self for method chaining
        """
        self._connect()
        
        # Create daemon thread - will automatically terminate when main exits
        thread = threading.Thread(target=self._update, daemon=True)
        thread.start()
        
        return self
    
    def _connect(self) -> bool:
        """
        Establish connection to video source.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Release existing stream if any
            if self._stream is not None:
                self._stream.release()
            
            print(f"[VideoGet] Connecting to {self.src}...")
            self._stream = cv2.VideoCapture(self.src)
            
            # Configure stream for lower latency
            if self._stream.isOpened():
                # Set buffer size to 1 to reduce latency
                self._stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._connected = True
                print("[VideoGet] ✓ Connected successfully")
                return True
            else:
                print("[VideoGet] ✗ Failed to open stream")
                self._connected = False
                return False
                
        except Exception as e:
            print(f"[VideoGet] ✗ Connection error: {e}")
            self._connected = False
            return False
    
    def _update(self) -> None:
        """
        Thread target: continuously grab frames and update the buffer.
        
        This method runs in a daemon thread and only stores the latest frame,
        preventing latency buildup from slow processing in the main loop.
        """
        consecutive_failures = 0
        max_failures = 10  # Trigger reconnect after this many failures
        
        while not self._stopped:
            # Handle disconnected state
            if not self._connected or self._stream is None:
                time.sleep(self.reconnect_delay)
                self._connect()
                continue
            
            try:
                grabbed, frame = self._stream.read()
                
                if grabbed and frame is not None:
                    # Update the latest frame (thread-safe)
                    with self._lock:
                        self._frame = frame
                        self._grabbed = True
                    
                    # Reset failure counter on success
                    consecutive_failures = 0
                    
                    # Update FPS stats
                    self._frame_count += 1
                    now = time.time()
                    elapsed = now - self._last_fps_time
                    if elapsed >= 1.0:
                        self._fps = self._frame_count / elapsed
                        self._frame_count = 0
                        self._last_fps_time = now
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        print("[VideoGet] Too many failures, attempting reconnect...")
                        self._connected = False
                        consecutive_failures = 0
                        
            except Exception as e:
                print(f"[VideoGet] Frame grab error: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    self._connected = False
                    consecutive_failures = 0
    
    def read(self) -> Optional[np.ndarray]:
        """
        Get the latest frame.
        
        Returns:
            The most recent frame as a numpy array, or None if no frame available
        """
        with self._lock:
            if self._grabbed and self._frame is not None:
                # Return a copy to prevent race conditions
                return self._frame.copy()
            return None
    
    def read_with_status(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Get the latest frame with connection status.
        
        Returns:
            Tuple of (is_connected, frame)
        """
        with self._lock:
            if self._grabbed and self._frame is not None:
                return (self._connected, self._frame.copy())
            return (self._connected, None)
    
    @property
    def fps(self) -> float:
        """Current frames per second being captured."""
        return self._fps
    
    @property
    def is_connected(self) -> bool:
        """Whether the stream is currently connected."""
        return self._connected
    
    def stop(self) -> None:
        """
        Stop the frame grabbing thread and release resources.
        """
        self._stopped = True
        
        # Give thread time to exit gracefully
        time.sleep(0.1)
        
        if self._stream is not None:
            self._stream.release()
            self._stream = None
        
        print("[VideoGet] Stopped")


# Quick test when run directly
if __name__ == "__main__":
    import sys
    
    # Default to local webcam for testing, or use command line arg
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    
    print(f"Testing VideoGet with source: {source}")
    video = VideoGet(src=source).start()
    
    try:
        while True:
            frame = video.read()
            if frame is not None:
                # Add FPS overlay
                cv2.putText(
                    frame, 
                    f"FPS: {video.fps:.1f}", 
                    (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1.0, 
                    (0, 255, 0), 
                    2
                )
                cv2.imshow("VideoGet Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        video.stop()
        cv2.destroyAllWindows()
