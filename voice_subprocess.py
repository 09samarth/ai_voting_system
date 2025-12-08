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
        
        # Step 1: Get Voter ID
        send_status(session_id, 1, 'listening', '🎤 LISTENING: Say your voter ID (TEST1, TEST2, etc.)')
        
        safe_print("About to speak welcome message")
        speak_subprocess_safe("Welcome to the voice voting system.")
        speak_subprocess_safe("You need to provide a voter ID first.")
        speak_subprocess_safe("Please say your voter ID clearly now.")
        speak_subprocess_safe("I am listening...")
        safe_print("Welcome message completed, starting voice recognition")
        
        safe_print("Calling listen() function with device_index=1")
        voter = listen(
            prefer_vosk=True,
            timeout=15,  # Longer timeout
            device_index=1,  # Working microphone
            should_stop=None,
            energy_threshold=None,
            dynamic_energy=True,
        )
        safe_print(f"listen() returned: {voter}")
        
        if not voter or not voter.strip():
            speak_subprocess_safe("I didn't hear you speak. Please make sure you are speaking clearly into your microphone.")
            speak_subprocess_safe("Please say your voter ID clearly.")
            speak_subprocess_safe("I will restart the process for you.")
            send_final_result(session_id, False, "No speech detected - please speak clearly. Try saying TEST1, TEST2, or TEST3.")
            return
        
        # Provide feedback that we heard something
        speak_subprocess_safe(f"I heard you say: {voter}")
        
        # Validate voter ID format - only accept 'first one' variations
        first_one_match = re.search(r'\b(first one|firstone|first van|first won|firs tone|asked one|ask one)\b', voter.lower())
        
        if not first_one_match:
            # Clear audio feedback for blind users - make it consistent with display
            error_message = f"Invalid Voter ID: I heard '{voter}'. Please provide a valid voter ID."
            
            # Debug: Log that we're about to speak
            safe_print(f"🔊 About to speak error message: {error_message}")
            
            # Speak the same message that will be displayed using Windows SAPI
            try:
                safe_print("🔊 Speaking error message with Windows SAPI...")
                speak_subprocess_safe(error_message)
                safe_print("🔊 Error message spoken")
                
                safe_print("🔊 Speaking additional guidance...")
                speak_subprocess_safe("Please provide a valid voter ID.")
                speak_subprocess_safe("Let me restart the process for you.")
                safe_print("🔊 Additional guidance spoken")
            except Exception as e:
                safe_print(f"❌ Error speaking messages: {e}")
                import traceback
                safe_print(f"❌ TTS Traceback: {traceback.format_exc()}")
            
            # Send the same message to the web interface
            send_final_result(session_id, False, error_message)
            return
        
        # Set valid voter ID for 'first one'
        valid_voter_id = "first one"  # Store as lowercase as requested
        send_status(session_id, 1, 'success', f'Voter ID confirmed: {valid_voter_id}')
        speak_subprocess_safe(f"Voter ID {valid_voter_id} confirmed")
        
        # Step 2: Get Candidate Choice
        send_status(session_id, 2, 'listening', '🎤 LISTENING: Say your candidate choice (1, 2, or 3)')
        
        candidates = get_candidates()
        speak_subprocess_safe("Excellent! Now I will read the list of candidates.")
        speak_subprocess_safe("Listen carefully to all candidates before making your choice.")
        for cid, name in candidates:
            speak_subprocess_safe(f"Candidate number {cid} is {name}")
        speak_subprocess_safe("Please say just the number of your chosen candidate.")
        speak_subprocess_safe("For example, say 1, or 2, or 3.")
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
        
        # Parse candidate choice - handle both digit and word forms
        # Map spoken number words to integers
        number_words = {
            'one': 1, 'won': 1, 'wan': 1,
            'two': 2, 'too': 2, 'to': 2,
            'three': 3, 'tree': 3, 'free': 3
        }
        
        candidate_id = None
        
        # First try to find a digit in the speech
        choice_match = re.search(r"(\d+)", choice)
        if choice_match:
            candidate_id = int(choice_match.group(1))
        else:
            # Try to find a number word
            choice_lower = choice.lower()
            for word, num in number_words.items():
                if word in choice_lower:
                    candidate_id = num
                    break
        
        if candidate_id is None:
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