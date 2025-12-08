#!/usr/bin/env python3
"""Test voter ID pattern matching"""
import re

def test_voter_id_patterns():
    """Test various voter ID patterns"""
    test_phrases = [
        "first one",
        "firstone", 
        "first van",
        "first won",
        "firs tone",
        "asked one",
        "ask one",
        "hello world",  # Should fail
        "test1",        # Should fail
        "last one",     # Should fail
    ]
    
    print("Testing voter ID pattern matching:")
    print("=" * 50)
    
    for phrase in test_phrases:
        # Same pattern as in voice_subprocess.py
        first_one_match = re.search(r'\b(first one|firstone|first van|first won|firs tone|asked one|ask one)\b', phrase.lower())
        
        if first_one_match:
            valid_voter_id = "first one"  # Store as lowercase
            result = "✅ VALID"
            print(f"'{phrase}' -> {result} (stored as: '{valid_voter_id}')")
        else:
            result = "❌ INVALID"
            print(f"'{phrase}' -> {result}")
    
    print("\n" + "=" * 50)
    print("Pattern matching test completed!")

if __name__ == "__main__":
    test_voter_id_patterns()