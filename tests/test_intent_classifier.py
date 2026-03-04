"""
Tests for AIVA Intent Classifier

Tests the rule-based intent classifier without loading heavy
dependencies (Whisper, pyttsx3, sounddevice).
"""
import sys
import os
from server.intent_classifier import IntentClassifier, Intent

# Initialize classifier
classifier = IntentClassifier()

def classify_intent(text: str) -> Intent:
    return classifier.classify(text)


def test_surroundings_intent():
    """Surroundings queries should classify correctly."""
    phrases = [
        "What's around me?",
        "what is around me",
        "tell me my surroundings",
        "what is nearby",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.SURROUNDINGS, f"'{phrase}' -> {result.value}, expected surroundings"
    print("  OK: Surroundings intent detected")


def test_read_text_intent():
    """Read text queries should classify correctly."""
    phrases = [
        "Read this text",
        "What does it say?",
        "read the sign",
        "read the label",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.READ_TEXT, f"'{phrase}' -> {result.value}, expected read_text"
    print("  OK: Read text intent detected")


def test_describe_intent():
    """Scene description queries should classify correctly."""
    phrases = [
        "Describe the scene",
        "What is in front of me?",
        "What do you see?",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.DESCRIBE, f"'{phrase}' -> {result.value}, expected describe"
    print("  OK: Describe intent detected")


def test_emergency_intent():
    """Emergency phrases should classify correctly."""
    phrases = [
        "Emergency!",
        "Help me!",
        "help",
        "SOS",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.EMERGENCY, f"'{phrase}' -> {result.value}, expected emergency"
    print("  OK: Emergency intent detected")


def test_location_intent():
    """Location queries should classify correctly."""
    phrases = [
        "Where am I?",
        "What is my location?",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.LOCATION, f"'{phrase}' -> {result.value}, expected location"
    print("  OK: Location intent detected")


def test_unknown_intent():
    """Unrecognized phrases should return UNKNOWN -- no guessing."""
    phrases = [
        "Play some music",
        "What time is it?",
        "Tell me a joke",
        "Calculate 5 plus 3",
        "",
        "   ",
    ]
    for phrase in phrases:
        result = classify_intent(phrase)
        assert result == Intent.UNKNOWN, f"'{phrase}' -> {result.value}, expected unknown"
    print("  OK: Unknown intent for unsupported phrases (no guessing)")


def test_empty_input():
    """Empty/whitespace input should return UNKNOWN."""
    assert classify_intent("") == Intent.UNKNOWN
    assert classify_intent("   ") == Intent.UNKNOWN
    assert classify_intent(None) == Intent.UNKNOWN  # type: ignore
    print("  OK: Empty input handled")


if __name__ == "__main__":
    print("=== Intent Classifier Tests ===\n")
    test_surroundings_intent()
    test_read_text_intent()
    test_describe_intent()
    test_emergency_intent()
    test_location_intent()
    test_unknown_intent()
    test_empty_input()
    print("\nAll intent classifier tests passed!")
