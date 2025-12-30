#!/usr/bin/env python3
"""
Voice Processing Subprocess
Handles voice recognition separately from web framework
"""
import sys
import json
import time
import os
import re
from voice_utils import listen, speak, speak_and_wait
from db import get_candidates, record_vote
from console_utils import safe_print
from windows_tts import speak_subprocess_safe

# ----------------------------
# Numeric state-coded voter IDs
# ----------------------------
# This demo uses synthetic, numeric-only voter identifiers.
# Format: StateCode-VoterNumber (e.g., 1-12, 2-45, 3-78)
# Users speak ONLY numbers; the first digit is the state code,
# remaining digits form the voter number.

NUM_WORD_TO_DIGIT = {
    "zero": "0",
    "oh": "0",   # common recognition for 0
    "o": "0",    # safety for "o" vs zero
    "one": "1",
    "two": "2",
    "too": "2",
    "to": "2",
    "three": "3",
    "four": "4",
    "for": "4",  # STT often hears "for" instead of "four"
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


def parse_state_coded_voter_id(transcript: str):
    """Parse spoken numeric voter ID into "StateCode-VoterNumber".

    Rules:
    - Accept ONLY numeric content (digits 0-9 or their word forms).
    - First digit is the state code.
    - Remaining digits form the voter number (normalized as an integer).

    Examples (spoken -> internal ID):
    - "one one two"   -> "1-12"
    - "two four five" -> "2-45"
    - "three seven eight" -> "3-78"
    """
    if not transcript:
        return None, None

    # Keep only alphanumeric tokens; reject anything that is not a digit word or digit.
    tokens = re.findall(r"[a-zA-Z0-9]+", transcript.lower())
    if not tokens:
        return None, None

    digits = []
    spoken_normalized_tokens = []  # what we will read back to the user

    for token in tokens:
        if token in NUM_WORD_TO_DIGIT:
            d = NUM_WORD_TO_DIGIT[token]
            digits.append(d)
            spoken_normalized_tokens.append(token)
        elif token.isdigit():
            # Split multi-digit strings into individual digits to preserve position
            for ch in token:
                digits.append(ch)
                spoken_normalized_tokens.append(ch)
        else:
            # Any non-numeric word makes this invalid by design
            return None, None

    if len(digits) < 2:
        # Need at least 1 digit for state + 1 for voter number
        return None, None

    digit_str = "".join(digits)
    state_code = digit_str[0]
    voter_number_str = digit_str[1:]

    try:
        voter_number_int = int(voter_number_str)
    except ValueError:
        return None, None

    voter_id = f"{state_code}-{voter_number_int}"
    spoken_normalized = " ".join(spoken_normalized_tokens)
    return voter_id, spoken_normalized


def capture_and_confirm_voter_id(session_id, max_attempts=3, confirm_attempts=2):
    """Capture a numeric state-coded voter ID with yes/no confirmation.

    Returns (voter_id, spoken_phrase) on success, (None, None) on failure.
    This function both provides rich audio feedback and updates status for the web UI.
    """
    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            send_status(
                session_id,
                1,
                'listening',
                '🎤 LISTENING: Say your numeric voter ID, digit by digit.'
            )
            safe_print("About to speak welcome message for numeric voter ID")
            speak_subprocess_safe("Welcome to the voice voting system.")
            speak_subprocess_safe("In this demo, your voter I D is numeric only.")
            speak_subprocess_safe(
                "Please say your voter I D as digits. Start with your state code digit, then say the remaining digits of your voter number."
            )
            speak_subprocess_safe("Say only numbers. Do not say any letters or special characters.")
            speak_subprocess_safe("I am listening for your voter I D now.")
        else:
            send_status(
                session_id,
                1,
                'listening',
                '🎤 LISTENING: Try again. Say only numbers for your voter I D.'
            )
            speak_subprocess_safe("Let's try again.")
            speak_subprocess_safe(
                "Please say your voter I D using only numbers. Start with your state code digit, then the remaining digits."
            )
            speak_subprocess_safe("I am listening...")

        safe_print("Starting listen() for numeric voter ID")
        voter_phrase = listen(
            prefer_vosk=True,
            timeout=15,
            device_index=1,
            should_stop=None,
            energy_threshold=None,
            dynamic_energy=True,
        )
        safe_print(f"listen() for voter ID returned: {voter_phrase}")

        if not voter_phrase or not voter_phrase.strip():
            speak_subprocess_safe("I did not hear any numbers.")
            if attempt == max_attempts:
                speak_subprocess_safe(
                    "I could not capture your voter I D. Please start a new session and try again."
                )
                send_final_result(
                    session_id,
                    False,
                    "No numeric voter I D detected. Please ensure your microphone is working and speak clearly.",
                )
                return None, None
            continue

        # Provide immediate feedback
        speak_subprocess_safe(f"I heard you say: {voter_phrase}")

        voter_id, spoken_normalized = parse_state_coded_voter_id(voter_phrase)
        safe_print(f"Parsed voter ID: {voter_id}, normalized phrase: {spoken_normalized}")

        if not voter_id:
            speak_subprocess_safe(
                "I can only accept numeric voter I D values, where you speak the digits one by one."
            )
            speak_subprocess_safe(
                "Please speak each digit separately, starting with your state code digit, and avoid any letters or extra words."
            )
            if attempt == max_attempts:
                send_final_result(
                    session_id,
                    False,
                    "Invalid voter I D format. Only numeric, state-coded I Ds are accepted in this demo.",
                )
                return None, None
            continue

        # Confirmation loop for this parsed ID
        for c_attempt in range(1, confirm_attempts + 1):
            # Requirement: feedback like "You said one one two. Is this correct?"
            speak_subprocess_safe(
                f"You said {spoken_normalized}. This maps to voter I D {voter_id}. Is this correct?"
            )
            speak_subprocess_safe("Say 'yes' to confirm or 'no' to try again.")
            safe_print("Listening for yes/no confirmation on voter ID")
            confirmation = listen(
                prefer_vosk=True,
                timeout=10,
                device_index=1,
                should_stop=None,
                energy_threshold=None,
                dynamic_energy=True,
            )
            safe_print(f"Confirmation listen() returned: {confirmation}")

            if not confirmation or not confirmation.strip():
                speak_subprocess_safe("I did not clearly hear yes or no.")
                if c_attempt == confirm_attempts:
                    break  # go back to outer loop and recapture the ID
                speak_subprocess_safe("Please say 'yes' if this is correct or 'no' if it is wrong.")
                continue

            confirmation_l = confirmation.lower()
            if "yes" in confirmation_l:
                send_status(session_id, 1, 'success', f'Voter ID confirmed: {voter_id}')
                speak_subprocess_safe(f"Voter I D {voter_id} confirmed.")
                return voter_id, spoken_normalized

            if "no" in confirmation_l:
                speak_subprocess_safe("Okay, we will try entering your voter I D again.")
                break  # break confirmation loop, go back to outer attempt loop

            speak_subprocess_safe(
                "I heard you, but I need you to say exactly 'yes' or 'no' to confirm your voter I D."
            )
            if c_attempt == confirm_attempts:
                # fall through to outer loop and recapture ID
                break

    # If we reach here, we have exhausted attempts
    send_final_result(
        session_id,
        False,
        "Unable to confirm a numeric state-coded voter I D after multiple attempts.",
    )
    return None, None

def send_status(session_id, step, status, message):
    """Send status update to web interface via file"""
    data = {
        'step': step,
        'status': status,
        'message': message,
        'timestamp': time.time()
    }
    
    status_file = f'status_{session_id}.json'
    try:
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        safe_print(f"Error writing status: {e}")

def send_final_result(session_id, success, message, voter_id=None, candidate=None):
    """Send final result to web interface via file"""
    data = {
        'success': success,
        'message': message,
        'voter_id': voter_id,
        'candidate': candidate,
        'step': 3,
        'status': 'completed' if success else 'error',
        'timestamp': time.time()
    }
    
    status_file = f'status_{session_id}.json'
    try:
        with open(status_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        safe_print(f"Error writing final result: {e}")

def voice_voting_process(session_id):
    """Complete voice voting process"""
    try:
        safe_print(f"Starting voice voting process for session {session_id}")
        
        # Step 1: Get numeric, state-coded Voter ID with confirmation
        valid_voter_id, spoken_voter_phrase = capture_and_confirm_voter_id(session_id)
        if not valid_voter_id:
            # capture_and_confirm_voter_id already sent an appropriate final result
            return
        
        # Step 2: Get Candidate Choice
        send_status(session_id, 2, 'listening', '🎤 LISTENING: Say your candidate choice (1, 2, or 3)')
        
        candidates = get_candidates()
        speak_subprocess_safe("Excellent! Now I will read the list of candidates.")
        speak_subprocess_safe("Listen carefully to all candidates before making your choice.")
        for cid, name in candidates:
            speak_subprocess_safe(f"Candidate number {cid} is {name}")
        speak_subprocess_safe("Please say just the number of your chosen candidate.")
        speak_subprocess_safe("I am listening for your choice...")
        
        choice = listen(
            prefer_vosk=True,
            timeout=15,  # Longer timeout
            device_index=1,
            should_stop=None,
            energy_threshold=None,
            dynamic_energy=True,
        )
        
        if not choice or not choice.strip():
            speak_subprocess_safe("I didn't hear your candidate choice clearly.")
            speak_subprocess_safe("Please say just the number: 1, 2, or 3.")
            speak_subprocess_safe("Let me try again.")
            send_final_result(session_id, False, "No candidate choice heard - please say 1, 2, or 3 clearly.")
            return
        
        # Provide feedback that we heard something
        speak_subprocess_safe(f"I heard you say: {choice}")
        
        # Parse candidate choice
        normalized_choice = (choice or "").lower().strip()

        # First try to extract an explicit digit (e.g., "1", "candidate 2")
        choice_match = re.search(r"\b(\d+)\b", normalized_choice)
        if choice_match:
            candidate_id = int(choice_match.group(1))
        else:
            # Also accept common spoken forms like "one", "two", "three"
            word_to_number = {
                "one": 1,
                "first": 1,
                "two": 2,
                "second": 2,
                "three": 3,
                "third": 3,
            }
            word_match = re.search(r"\b(one|first|two|second|three|third)\b", normalized_choice)
            if word_match:
                candidate_id = word_to_number[word_match.group(1)]
            else:
                # Clear audio feedback for blind users - make it consistent with display
                error_message = f"Invalid candidate choice: I heard '{choice}'. Please say just the number: 1, 2, or 3."
                
                # Speak the same message that will be displayed
                speak_subprocess_safe(error_message)
                speak_subprocess_safe("Please say exactly: 1, 2, or 3.")
                speak_subprocess_safe("Let me restart the candidate selection for you.")
                send_final_result(session_id, False, error_message)
                return
        
        # Find candidate name
        candidate_name = None
        for cid, name in candidates:
            if cid == candidate_id:
                candidate_name = name
                break
        
        if not candidate_name:
            send_final_result(session_id, False, f"Invalid candidate number: {candidate_id}")
            return
        
        send_status(session_id, 2, 'success', f'Candidate selected: {candidate_name}')
        speak_subprocess_safe(f"You selected {candidate_name}")
        
        # Step 3: Confirmation
        send_status(session_id, 3, 'listening', '🎤 LISTENING: Say "confirm" to cast your vote or "cancel" to abort')
        
        speak_subprocess_safe(f"Perfect! You have chosen {candidate_name}.")
        speak_subprocess_safe("Now I need your final confirmation to cast your vote.")
        speak_subprocess_safe("Say 'confirm' to cast your vote for this candidate.")
        speak_subprocess_safe("Or say 'cancel' to abort and not vote.")
        speak_subprocess_safe("I am listening for your confirmation...")
        
        confirmation = listen(
            prefer_vosk=True,
            timeout=15,  # Longer timeout for confirmation
            device_index=1,
            should_stop=None,
            energy_threshold=None,
            dynamic_energy=True,
        )
        
        if not confirmation:
            speak_subprocess_safe("I didn't hear your confirmation clearly.")
            speak_subprocess_safe("Please say 'confirm' to cast your vote, or 'cancel' to abort.")
            speak_subprocess_safe("Let me try again.")
            send_final_result(session_id, False, "No confirmation heard. Say 'confirm' to vote or 'cancel' to abort.")
            return
        
        # Provide feedback that we heard something
        speak_subprocess_safe(f"I heard you say: {confirmation}")
        
        if "confirm" in confirmation.lower():
            # Record the vote
            record_vote(valid_voter_id, candidate_id)
            speak_subprocess_safe("Excellent! Your vote has been successfully recorded.")
            speak_subprocess_safe(f"You voted for {candidate_name}.")
            speak_subprocess_safe("Thank you for voting!")
            send_final_result(session_id, True, f"Vote successfully recorded for {candidate_name}!", valid_voter_id, candidate_name)
        else:
            # Clear audio feedback for blind users - make it consistent with display
            error_message = f"Vote cancelled: I heard '{confirmation}' but need 'confirm' to vote."
            
            # Speak the same message that will be displayed
            speak_subprocess_safe(error_message)
            speak_subprocess_safe("Your vote has been cancelled for security.")
            speak_subprocess_safe("Please start again if you want to vote.")
            send_final_result(session_id, False, error_message)
            
    except Exception as e:
        safe_print(f"Exception in voice_voting_process: {str(e)}")
        safe_print(f"Exception type: {type(e).__name__}")
        import traceback
        safe_print(f"Traceback: {traceback.format_exc()}")
        send_final_result(session_id, False, f"Error during voice voting: {str(e)}")

def main():
    """Main function"""
    safe_print(f"Voice subprocess started with args: {sys.argv}")
    
    if len(sys.argv) != 2:
        safe_print("Usage: python voice_subprocess.py <session_id>")
        return
    
    session_id = sys.argv[1]
    safe_print(f"Processing session ID: {session_id}")
    
    try:
        # Start voice voting process
        voice_voting_process(session_id)
        
    except Exception as e:
        safe_print(f"Main exception: {str(e)}")
        import traceback
        safe_print(f"Main traceback: {traceback.format_exc()}")
        send_final_result(session_id, False, f"Voice voting failed: {str(e)}")

if __name__ == "__main__":
    main()