"""
AIVA Server — Intent Classifier
==================================
Rule-based NLP engine for detecting user intents from transcribed text.

Supports:
- EMERGENCY (SOS, Help, Danger)
- LOCATION (Where am I, GPS)
- SURROUNDINGS (What's around me)
- READ_TEXT (OCR)
- DESCRIBE (Scene description)
"""

import re
import logging
from enum import Enum
from typing import List, Tuple, Optional

logger = logging.getLogger("aiva.nlp")

class Intent(Enum):
    """User intent categories."""
    SURROUNDINGS = "surroundings"
    READ_TEXT = "read_text"
    DESCRIBE = "describe"
    EMERGENCY = "emergency"
    LOCATION = "location"
    BATTERY = "battery"
    INTERNET = "internet"
    UNKNOWN = "unknown"

class IntentClassifier:
    """
    Regex-based intent classifier.
    Fast, deterministic, and offline-capable.
    """

    # Patterns ordered by specificity/priority
    # (regex, Intent)
    INTENT_PATTERNS: List[Tuple[str, Intent]] = [
        # High Priority
        (r"\b(emergency|help me|help|danger|sos|call 911|i need help)\b", Intent.EMERGENCY),
        (r"\b(where am i|location|gps|address|coordinates)\b", Intent.LOCATION),
        
        # Vision / General
        (r"\b(around me|surroundings|what'?s around|nearby|around)\b", Intent.SURROUNDINGS),
        (r"\b(what is near|what'?s near)\b", Intent.SURROUNDINGS),
        (r"\b(read|text|what does it say|ocr|sign|label|board)\b", Intent.READ_TEXT),
        (r"\b(describe|scene|what'?s in front|front of me|look|see)\b", Intent.DESCRIBE),
        (r"\b(what is this|what is that|what do you see)\b", Intent.DESCRIBE),
        
        # System
        (r"\b(battery|power|charge)\b", Intent.BATTERY),
        (r"\b(internet|network|connection|wifi|online)\b", Intent.INTERNET),
    ]

    def classify(self, text: Optional[str]) -> Intent:
        """
        Classify input text into an Intent.

        Args:
            text: Transcribed speech text

        Returns:
            Detected Intent or Intent.UNKNOWN
        """
        if not text or not text.strip():
            return Intent.UNKNOWN

        text_lower = text.lower().strip()
        
        # Normalize punctuation/quotes
        text_lower = text_lower.replace('\u2019', "'").replace('\u2018', "'")
        
        for pattern, intent in self.INTENT_PATTERNS:
            if re.search(pattern, text_lower):
                logger.debug(f"Detected intent '{intent.name}' in: '{text}'")
                return intent
        
        return Intent.UNKNOWN
