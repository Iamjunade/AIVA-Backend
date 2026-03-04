"""
AIVA Server — Recognition Engine
====================================
Gemini-powered identification of currency notes, documents, and products.

Uses Google Gemini 2.0 Flash multimodal vision to visually identify
objects that a blind user points their camera at. This goes far beyond
OCR — it can recognize currency denominations by visual features,
identify product brands by logos, and classify document types.

Design Constraints:
    - User-triggered ONLY — activated by IDENTIFY intent
    - Anti-hallucination: only describe what is clearly visible
    - Concise output: max 2 sentences, optimized for TTS delivery
    - Graceful degradation if Gemini is unavailable
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("aiva.recognition")


# =============================================================================
# CATEGORY DETECTION
# =============================================================================

class RecognitionCategory:
    """Categories for the recognition engine."""
    CURRENCY = "currency"
    DOCUMENT = "document"
    PRODUCT = "product"
    GENERAL = "general"


# Keywords used to determine which specialized prompt to use
_CURRENCY_KEYWORDS = {
    "currency", "money", "note", "bill", "coin", "rupee", "dollar",
    "cash", "denomination", "how much", "worth",
}
_DOCUMENT_KEYWORDS = {
    "document", "paper", "card", "id card", "license", "passport",
    "certificate", "letter", "form", "receipt", "ticket",
}
_PRODUCT_KEYWORDS = {
    "product", "brand", "package", "bottle", "can", "box", "item",
    "medicine", "food", "drink", "snack",
}


def detect_category(user_query: str) -> str:
    """
    Determine the recognition category from the user's query.

    Args:
        user_query: The user's spoken/typed request

    Returns:
        RecognitionCategory string
    """
    query_lower = user_query.lower()
    words = set(re.findall(r'\b\w+\b', query_lower))

    if words & _CURRENCY_KEYWORDS:
        return RecognitionCategory.CURRENCY
    if words & _DOCUMENT_KEYWORDS:
        return RecognitionCategory.DOCUMENT
    if words & _PRODUCT_KEYWORDS:
        return RecognitionCategory.PRODUCT
    return RecognitionCategory.GENERAL


# =============================================================================
# PROMPTS — Specialized per category
# =============================================================================

_BASE_RULES = (
    "CRITICAL RULES:\n"
    "1. Base your answer SOLELY on what is visible in the image.\n"
    "2. If you cannot clearly identify it, say so honestly. Never guess.\n"
    "3. Keep your response to 1-2 SHORT sentences. It will be spoken aloud.\n"
    "4. Do NOT use markdown, bullet points, or formatting.\n"
    "5. Speak naturally as a helpful companion.\n"
)

PROMPTS = {
    RecognitionCategory.CURRENCY: (
        "You are AIVA, an AI assistant for a blind user. "
        "The user is holding a currency note or coin in front of the camera.\n\n"
        "Identify:\n"
        "- The denomination (e.g., 500, 100, 2000)\n"
        "- The currency (e.g., Indian Rupees, US Dollars)\n"
        "- Which side is visible (front or back), if applicable\n\n"
        + _BASE_RULES +
        "\nExample good responses:\n"
        "- 'This is a 500 Indian rupee note, front side.'\n"
        "- 'This looks like a 10 US dollar bill.'\n"
        "- 'I can see a coin but cannot determine the denomination clearly.'"
    ),

    RecognitionCategory.DOCUMENT: (
        "You are AIVA, an AI assistant for a blind user. "
        "The user is showing a document, card, or paper to the camera.\n\n"
        "Identify:\n"
        "- The type of document (ID card, passport, letter, receipt, etc.)\n"
        "- The most important visible text (name, title, date, amount)\n"
        "- The issuing organization, if visible\n\n"
        + _BASE_RULES +
        "\nExample good responses:\n"
        "- 'This is an Aadhaar card. The name reads Junaid Pasha.'\n"
        "- 'This is a medical prescription from Apollo Hospital.'\n"
        "- 'This appears to be a receipt. The total amount is 450 rupees.'"
    ),

    RecognitionCategory.PRODUCT: (
        "You are AIVA, an AI assistant for a blind user. "
        "The user is showing a product, package, or item to the camera.\n\n"
        "Identify:\n"
        "- The brand name\n"
        "- The product name\n"
        "- Key details (size, flavor, dosage if medicine)\n\n"
        + _BASE_RULES +
        "\nExample good responses:\n"
        "- 'This is a Paracetamol 500mg tablet strip by Cipla.'\n"
        "- 'This is a 330ml Coca-Cola can.'\n"
        "- 'This is a Maggi 2-minute noodles pack, masala flavor.'"
    ),

    RecognitionCategory.GENERAL: (
        "You are AIVA, an AI assistant for a blind user. "
        "The user is holding or pointing at an object and wants to know what it is.\n\n"
        "Identify the object as specifically as possible:\n"
        "- What is it?\n"
        "- Any text, brand, or distinguishing features visible?\n"
        "- Color, size, or shape if helpful\n\n"
        + _BASE_RULES +
        "\nExample good responses:\n"
        "- 'This is a set of keys on a metal keyring.'\n"
        "- 'This is a blue pen, looks like a Reynolds brand.'\n"
        "- 'This is a TV remote control with many buttons.'"
    ),
}


# =============================================================================
# RECOGNITION ENGINE
# =============================================================================

class RecognitionEngine:
    """
    Gemini-powered object/currency/document/product recognition.

    Uses the existing AssistantAI infrastructure to send frames to
    Gemini with specialized prompts based on what the user is asking about.
    """

    def __init__(self):
        """Initialize the recognition engine with Gemini."""
        self._model = None
        self._initialize_gemini()

    def _initialize_gemini(self):
        """Initialize Gemini model for recognition."""
        try:
            import google.generativeai as genai
            import os
            from dotenv import load_dotenv
            from pathlib import Path

            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)

            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key or api_key == "your_api_key_here":
                logger.warning("[RecognitionEngine] No Gemini API key — disabled")
                return

            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            logger.info("[RecognitionEngine] ✓ Gemini model ready")
        except Exception as e:
            logger.error(f"[RecognitionEngine] ✗ Gemini init failed: {e}")

    @property
    def is_available(self) -> bool:
        """Whether the recognition engine is ready."""
        return self._model is not None

    def identify(
        self,
        image_bytes: bytes,
        user_query: str = "",
    ) -> str:
        """
        Identify an object, currency, document, or product in an image.

        Args:
            image_bytes: JPEG image bytes from the camera
            user_query: The user's spoken query (used for category detection)

        Returns:
            Natural language identification string for TTS
        """
        if not self.is_available:
            return "Recognition is not available right now."

        # Determine category from user query
        category = detect_category(user_query) if user_query else RecognitionCategory.GENERAL
        prompt = PROMPTS[category]

        logger.info(f"[RecognitionEngine] Category: {category}, query: '{user_query}'")

        try:
            import PIL.Image
            import io

            # Convert JPEG bytes to PIL Image
            image = PIL.Image.open(io.BytesIO(image_bytes))

            # Resize for faster API response (same strategy as AssistantAI)
            max_size = 512
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, PIL.Image.LANCZOS)

            # Send to Gemini
            response = self._model.generate_content(
                [prompt, image],
                generation_config={
                    "max_output_tokens": 100,
                    "temperature": 0.2,  # Low temp for factual identification
                },
            )

            text = response.text.strip()
            # Clean up
            text = text.replace("**", "").replace("*", "").strip()
            # Cap length for TTS
            if len(text) > 150:
                text = text[:147] + "..."

            logger.info(f"[RecognitionEngine] Result: '{text}'")
            return text if text else "I couldn't identify that clearly. Try holding it closer."

        except Exception as e:
            logger.error(f"[RecognitionEngine] Identification failed: {e}")
            return "I had trouble identifying that. Please try again."
