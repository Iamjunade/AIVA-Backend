import requests
import json
import time

# Zhipu AI / BigModel Key
API_KEY = "5b6e33640049476ab7ae88741268b474.7iE13LmhqWrGQbzk"

# Generate JWT (Zhipu requires this unique auth format if not using OpenAI SDK)
# BUT! Their OpenAI-compatible endpoint accepts the raw key usually.
# Let's try the pure OpenAI endpoint method first manually.

url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "glm-4",
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

print("Testing Zhipu Raw Request...")
try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
