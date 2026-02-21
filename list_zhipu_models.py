from openai import OpenAI
import os
import sys

# Use UTF-8 for output
sys.stdout.reconfigure(encoding='utf-8')

# Your Zhipu Key
API_KEY = "5b6e33640049476ab7ae88741268b474.7iE13LmhqWrGQbzk"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"

print(f"Checking models for key: {API_KEY[:8]}...")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)

try:
    models = client.models.list()
    print("\n--- AVAILABLE MODELS ---")
    for m in models:
        print(f"ID: {m.id}")
    print("------------------------")
except Exception as e:
    print(f"Error listing models: {e}")
