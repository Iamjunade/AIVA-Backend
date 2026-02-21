"""Simple test script to verify Google Gemini API key is working."""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Testing API Key: {api_key[:10]}...{api_key[-4:]}")

# Configure the API
genai.configure(api_key=api_key)

# Test the API with a simple request
try:
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Say 'Hello! The API key is working correctly.' in exactly those words.")
    print(f"\n✓ API Response: {response.text}")
    print("\n✅ API KEY TEST PASSED - The Gemini API key is valid and working!")
except Exception as e:
    print(f"\n❌ API KEY TEST FAILED: {e}")
