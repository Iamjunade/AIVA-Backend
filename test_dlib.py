"""Test dlib face detection with different image formats."""
import cv2
import numpy as np
from PIL import Image
import io
import face_recognition

print("Testing dlib face detection...")

# Capture a frame
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

if not ret:
    print("Failed to capture frame")
    exit(1)

print(f"Original frame: shape={frame.shape}, dtype={frame.dtype}")

# Resize
small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
print(f"Resized frame: shape={small.shape}, dtype={small.dtype}")

# Method 1: Direct BGR to RGB
print("\n--- Method 1: Direct cv2.cvtColor ---")
try:
    rgb1 = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    rgb1 = np.ascontiguousarray(rgb1, dtype=np.uint8)
    print(f"RGB array: shape={rgb1.shape}, dtype={rgb1.dtype}, contiguous={rgb1.flags['C_CONTIGUOUS']}")
    locs = face_recognition.face_locations(rgb1)
    print(f"SUCCESS! Faces found: {locs}")
except Exception as e:
    print(f"FAILED: {e}")

# Method 2: Via JPEG buffer
print("\n--- Method 2: JPEG buffer + PIL ---")
try:
    _, buf = cv2.imencode('.jpg', small)
    img = Image.open(io.BytesIO(buf.tobytes())).convert('RGB')
    rgb2 = np.array(img, dtype=np.uint8)
    rgb2 = np.ascontiguousarray(rgb2)
    print(f"RGB array: shape={rgb2.shape}, dtype={rgb2.dtype}, contiguous={rgb2.flags['C_CONTIGUOUS']}")
    locs = face_recognition.face_locations(rgb2)
    print(f"SUCCESS! Faces found: {locs}")
except Exception as e:
    print(f"FAILED: {e}")

# Method 3: Save to disk and load
print("\n--- Method 3: Save to disk ---")
try:
    cv2.imwrite('test_frame.jpg', small)
    img = face_recognition.load_image_file('test_frame.jpg')
    print(f"Loaded image: shape={img.shape}, dtype={img.dtype}")
    locs = face_recognition.face_locations(img)
    print(f"SUCCESS! Faces found: {locs}")
    import os
    os.remove('test_frame.jpg')
except Exception as e:
    print(f"FAILED: {e}")

print("\nTest complete!")
