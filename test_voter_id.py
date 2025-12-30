#!/usr/bin/env python3
"""Test numeric state-coded voter ID parsing"""
from voice_subprocess import parse_state_coded_voter_id

def test_voter_id_patterns():
    """Test various spoken voter ID patterns for the numeric scheme"""
    test_phrases = [
        # Expected to succeed (examples from the spec)
        "one one two",          # -> 1-12
        "two four five",        # -> 2-45
        "three seven eight",    # -> 3-78
        # Mixed digits and words
        "1 1 2",                # -> 1-12
        "two 45",               # -> 2-45
        "3 7 8",                # -> 3-78
        # Edge / numeric-only variations
        "zero zero one",        # -> 0-1
        "9 0 0",                # -> 9-0
        # Invalid (should fail parsing)
        "hello world",
        "first one",            # old scheme, no longer valid
        "test1",
        "one two three x",      # extra non-numeric token
        "",                     # empty
    ]
    
    print("Testing numeric state-coded voter ID parsing:")
    print("=" * 60)
    
    for phrase in test_phrases:
        voter_id, spoken_norm = parse_state_coded_voter_id(phrase)
        if voter_id:
            result = "✅ PARSED"
            print(f"'{phrase}' -> {result}: internal='{voter_id}', spoken='{spoken_norm}'")
        else:
            result = "❌ REJECTED"
            print(f"'{phrase}' -> {result}")
    
    print("\n" + "=" * 60)
    print("Numeric voter ID parsing test completed!")

if __name__ == "__main__":
    test_voter_id_patterns()
