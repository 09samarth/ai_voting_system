import os
from pathlib import Path
import pyttsx3
import threading
import time
import atexit
import signal
import sys
import speech_recognition as sr
from console_utils import safe_print

# TTS
engine = pyttsx3.init()
_engine_lock = threading.Lock()


def _shutdown_tts():
    # Ensure pyttsx3 background loop is stopped on process exit
    try:
        with _engine_lock:
            engine.stop()
    except Exception:
        pass

# Track last PyAudio instance to ensure clean termination
_last_pyaudio = None

def _force_exit():
    """Force exit when hanging"""
    try:
        safe_print("\n🛑 Force cleanup in progress...")
        _shutdown_tts()
        _shutdown_audio()
        safe_print("✅ Cleanup complete!")
    except Exception:
        pass
    safe_print("👋 Exiting...")
    os._exit(0)

def _signal_handler(signum, frame):
    """Handle Ctrl+C more aggressively"""
    print("\nReceived interrupt signal. Cleaning up...")
    _force_exit()

def _shutdown_audio():
    global _last_pyaudio
    try:
        if _last_pyaudio is not None:
            _last_pyaudio.terminate()
    except Exception:
        pass
    finally:
        _last_pyaudio = None

def _cleanup_all():
    """Comprehensive cleanup function"""
    print("Cleaning up resources...")
    _shutdown_tts()
    _shutdown_audio()
    # Force flush any pending output
    sys.stdout.flush()
    sys.stderr.flush()

# Register cleanup handlers
atexit.register(_cleanup_all)

# Enhanced signal handling for better Ctrl+C response
def _setup_signal_handlers():
    """Setup signal handlers with better error handling"""
    try:
        # Only setup signal handlers in the main thread
        if threading.current_thread() is threading.main_thread():
            # Handle Ctrl+C (SIGINT) and termination (SIGTERM)
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
            
            # On Windows, also handle SIGBREAK
            if hasattr(signal, 'SIGBREAK'):
                signal.signal(signal.SIGBREAK, _signal_handler)
        else:
            # In non-main threads, just register cleanup without signal handling
            pass
            
    except (OSError, ValueError) as e:
        # Signal handling might not be available in some environments
        print(f"Warning: Could not setup signal handlers: {e}")

# Setup signal handlers only if we're in the main thread
if threading.current_thread() is threading.main_thread():
    _setup_signal_handlers()

def speak(text):
    """Speak text using TTS engine with proper error handling"""
    safe_print(f"🔊 speak() called with: '{text}'")
    
    # Prevent re-entrant run loop errors under Streamlit's multi-run model
    with _engine_lock:
        try:
            safe_print("🔊 Calling engine.say()...")
            engine.say(text)
            safe_print("🔊 Calling engine.runAndWait()...")
            engine.runAndWait()
            safe_print("🔊 Calling engine.stop()...")
            # Ensure the engine is completely stopped before returning
            engine.stop()
            # Additional cleanup to prevent audio conflicts
            import time
            time.sleep(0.5)  # Extra delay to ensure audio system is free
            safe_print("✅ speak() completed successfully")
        except RuntimeError as e:
            msg = str(e).lower()
            safe_print(f"⚠️ RuntimeError in speak(): {e}")
            if "run loop already started" in msg:
                # Wait for current speech to finish, then try once more
                safe_print("🔄 Waiting for engine to be free...")
                while engine.isBusy():
                    time.sleep(0.05)
                safe_print("🔄 Retrying speech...")
                engine.say(text)
                engine.runAndWait()
                engine.stop()
                import time
                time.sleep(0.5)  # Extra delay
                safe_print("✅ speak() retry completed")
            else:
                safe_print(f"❌ Unhandled RuntimeError: {e}")
                raise
        except Exception as e:
            safe_print(f"❌ Error in speak(): {e}")
            import traceback
            safe_print(f"❌ Traceback: {traceback.format_exc()}")
            raise

def speak_and_wait(text, wait_time=2.0):
    """Speak text and wait for audio system to be completely free"""
    speak(text)
    import time
    time.sleep(wait_time)  # Additional wait time for audio system cleanup

# ASR
try:
    from vosk import Model, KaldiRecognizer
    import pyaudio
    VOSK_AVAILABLE = True
except Exception:
    VOSK_AVAILABLE = False

MODEL_DIR = Path(__file__).parent / "models" / "vosk-model-small-en-us-0.15"

def recognize_from_vosk(seconds=5, sample_rate=16000, should_stop=None, device_index=None):
    safe_print(f"🤖 Starting Vosk recognition: timeout={seconds}s, sample_rate={sample_rate}, device_index={device_index}")
    
    if not VOSK_AVAILABLE:
        safe_print("❌ Vosk not available")
        return None
    if not MODEL_DIR.exists():
        safe_print(f"❌ Vosk model not found at: {MODEL_DIR}")
        return None

    global _last_pyaudio
    
    try:
        safe_print("🔄 Loading Vosk model...")
        model = Model(str(MODEL_DIR))
        safe_print("✅ Vosk model loaded")
        
        p = pyaudio.PyAudio()
        _last_pyaudio = p
        stream = None
        
        try:
            safe_print(f"🎤 Opening audio stream at {sample_rate}Hz...")
            try:
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=sample_rate,
                                input=True, frames_per_buffer=8000,
                                input_device_index=device_index)
                actual_rate = sample_rate
                safe_print(f"✅ Audio stream opened at {actual_rate}Hz")
            except Exception as e:
                safe_print(f"⚠️ Failed to open stream at {sample_rate}Hz: {e}")
                # Device may not support 16k; fall back to 44100 and resample via recognizer model
                safe_print("🔄 Trying fallback rate 44100Hz...")
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100,
                                input=True, frames_per_buffer=8192,
                                input_device_index=device_index)
                actual_rate = 44100
                safe_print(f"✅ Audio stream opened at {actual_rate}Hz (fallback)")
                
            stream.start_stream()
            rec = KaldiRecognizer(model, actual_rate)
            safe_print(f"🎤 Recording for {seconds} seconds...")

            transcript = ""
            import time as _t, json
            t_end = _t.time() + seconds
            chunks_processed = 0
            
            while _t.time() < t_end:
                if callable(should_stop) and should_stop():
                    safe_print("🛑 Recording stopped by request")
                    break
                    
                try:
                    data = stream.read(4000, exception_on_overflow=False)
                    chunks_processed += 1
                    
                    if rec.AcceptWaveform(data):
                        res = rec.Result()
                        j = json.loads(res)
                        partial_text = j.get("text", "")
                        if partial_text:
                            transcript += " " + partial_text
                            safe_print(f"🗣️ Partial result: '{partial_text}'")
                            
                except Exception as e:
                    safe_print(f"⚠️ Error reading audio chunk: {e}")
                    continue

            safe_print(f"🏁 Recording finished. Processed {chunks_processed} audio chunks.")
            
            # Get final result
            try:
                final = rec.FinalResult()
                j = json.loads(final)
                final_text = j.get("text", "")
                if final_text:
                    transcript += " " + final_text
                    safe_print(f"🏁 Final result: '{final_text}'")
            except Exception as e:
                safe_print(f"⚠️ Error getting final result: {e}")

            transcript = transcript.strip()
            result = transcript.lower() if transcript else None
            
            if result:
                safe_print(f"✅ Vosk recognition successful: '{result}'")
            else:
                safe_print("❌ No speech detected by Vosk")
                
            return result
            
        finally:
            try:
                if stream is not None:
                    if stream.is_active():
                        stream.stop_stream()
                    stream.close()
                    safe_print("🔧 Audio stream closed")
            except Exception as e:
                safe_print(f"⚠️ Error closing stream: {e}")
            try:
                p.terminate()
                safe_print("🔧 PyAudio terminated")
            except Exception as e:
                safe_print(f"⚠️ Error terminating PyAudio: {e}")
            _last_pyaudio = None
            
    except Exception as e:
        safe_print(f"❌ Vosk recognition failed: {e}")
        return None


def recognize_with_google(timeout=6, device_index=None, should_stop=None, energy_threshold=None, dynamic_energy=True):
    safe_print(f"🌐 Starting Google recognition: timeout={timeout}s, device_index={device_index}")
    
    r = sr.Recognizer()
    r.dynamic_energy_threshold = dynamic_energy
    if energy_threshold is not None:
        r.energy_threshold = energy_threshold
        safe_print(f"🔧 Set manual energy threshold: {energy_threshold}")
    
    mic_kwargs = {}
    if device_index is not None:
        mic_kwargs["device_index"] = device_index
        
    try:
        with sr.Microphone(**mic_kwargs) as source:
            safe_print("🔧 Adjusting for ambient noise...")
            try:
                r.adjust_for_ambient_noise(source, duration=0.5)
                safe_print(f"📊 Energy threshold adjusted to: {r.energy_threshold}")
            except Exception as e:
                safe_print(f"⚠️ Could not adjust for ambient noise: {e}")
                
            import time as _t
            deadline = _t.time() + timeout
            attempts = 0
            
            # Poll in short chunks so we can honor stop requests
            while _t.time() < deadline and not (callable(should_stop) and should_stop()):
                attempts += 1
                remaining = max(0.5, min(2.0, deadline - _t.time()))
                safe_print(f"🎤 Listening attempt #{attempts}, {remaining:.1f}s remaining...")
                
                try:
                    # Listen for audio with proper timeout handling
                    audio = r.listen(source, timeout=1, phrase_time_limit=remaining)
                    safe_print("📡 Audio captured, sending to Google...")
                    
                    # Try to recognize with Google
                    text = r.recognize_google(audio).lower()
                    if text and text.strip():
                        safe_print(f"✅ Google recognition successful: '{text}'")
                        return text
                    else:
                        safe_print("⚠️ Google returned empty result")
                        
                except sr.UnknownValueError:
                    safe_print("❌ Google could not understand the audio")
                    continue
                except sr.RequestError as e:
                    safe_print(f"❌ Google service error: {e}")
                    return None  # Don't continue if service is down
                except sr.WaitTimeoutError:
                    safe_print("⏰ Listen timeout - no audio detected")
                    continue
                except Exception as e:
                    safe_print(f"❌ Unexpected error during Google recognition: {e}")
                    continue
                    
            safe_print(f"⏰ Google recognition timeout after {attempts} attempts")
            return None
            
    except Exception as e:
        safe_print(f"❌ Failed to initialize microphone for Google recognition: {e}")
        return None


def listen(prefer_vosk=True, timeout=6, device_index=None, should_stop=None, energy_threshold=None, dynamic_energy=True):
    safe_print(f"🎤 Listen function called: prefer_vosk={prefer_vosk}, timeout={timeout}, should_stop={should_stop}")
    
    # Try Vosk first if available
    if prefer_vosk and VOSK_AVAILABLE and MODEL_DIR.exists():
        safe_print("🔍 Trying Vosk recognition...")
        t = recognize_from_vosk(seconds=timeout, should_stop=should_stop, device_index=device_index)
        safe_print(f"🔍 Vosk result: '{t}'")
        if t and t.strip():
            safe_print("✅ Vosk recognition successful!")
            return t
        else:
            safe_print("❌ Vosk recognition failed, falling back to Google...")
    else:
        safe_print("🔍 Vosk not available or not preferred, using Google...")
    
    # Fallback to Google if Vosk failed or not preferred
    safe_print("🔍 Trying Google recognition...")
    result = recognize_with_google(
        timeout=timeout,
        device_index=device_index,
        should_stop=should_stop,
        energy_threshold=energy_threshold,
        dynamic_energy=dynamic_energy,
    )
    safe_print(f"🔍 Google result: '{result}'")
    return result


def test_microphone(seconds=3, device_index=None, energy_threshold=None, dynamic_energy=True):
    return recognize_with_google(
        timeout=seconds,
        device_index=device_index,
        should_stop=None,
        energy_threshold=energy_threshold,
        dynamic_energy=dynamic_energy,
    )

def monitor_audio_levels(seconds=10, device_index=None, sample_rate=16000):
    """Monitor audio levels to help users check if their microphone is working"""
    safe_print(f"📊 Starting audio level monitoring for {seconds} seconds...")
    
    try:
        import pyaudio
        import numpy as np
        import time
        
        p = pyaudio.PyAudio()
        
        # Try to open the audio stream
        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                frames_per_buffer=1024,
                input_device_index=device_index
            )
        except Exception as e:
            safe_print(f"❌ Failed to open audio stream: {e}")
            p.terminate()
            return False
            
        safe_print("🗣️ Please speak or make noise near your microphone...")
        safe_print("📊 Audio level bars (speak to see activity):")
        
        stream.start_stream()
        start_time = time.time()
        max_level = 0
        samples_processed = 0
        
        try:
            while time.time() - start_time < seconds:
                try:
                    # Read audio data
                    data = stream.read(1024, exception_on_overflow=False)
                    
                    # Convert to numpy array and calculate RMS level
                    audio_data = np.frombuffer(data, dtype=np.int16)
                    if len(audio_data) > 0:
                        rms = np.sqrt(np.mean(audio_data.astype(np.float64)**2))
                        # Handle NaN values
                        if np.isnan(rms) or np.isinf(rms):
                            rms = 0.0
                    else:
                        rms = 0.0
                    
                    # Convert to a scale of 0-100
                    level = min(100, max(0, int((rms / 3000) * 100)))
                    max_level = max(max_level, level)
                    samples_processed += 1
                    
                    # Create a simple bar visualization
                    bar_length = min(50, level // 2)
                    bar = '█' * bar_length + '░' * (25 - bar_length)
                    
                    # Print level with carriage return for live update
                    try:
                        print(f"\r📊 [{bar}] {level:3d}% (max: {max_level:3d}%)", end="", flush=True)
                    except UnicodeEncodeError:
                        # Fallback for Windows compatibility
                        simple_bar = '#' * bar_length + '-' * (25 - bar_length)
                        print(f"\r[CHART] [{simple_bar}] {level:3d}% (max: {max_level:3d}%)", end="", flush=True)
                    
                    time.sleep(0.1)  # Update 10 times per second
                    
                except Exception as e:
                    safe_print(f"\n⚠️ Error reading audio: {e}")
                    continue
                    
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()
            
        print(f"\n\n📊 Monitoring complete!")
        print(f"📈 Processed {samples_processed} audio samples")
        print(f"🔊 Maximum audio level detected: {max_level}%")
        
        if max_level < 5:
            print("❌ Very low audio levels detected. Check your microphone:")
            print("   • Make sure it's not muted")
            print("   • Check microphone permissions")
            print("   • Try speaking louder or closer to the microphone")
            return False
        elif max_level < 20:
            print("⚠️ Low audio levels detected. Consider:")
            print("   • Speaking louder or closer to the microphone")
            print("   • Adjusting microphone sensitivity")
            return True
        else:
            print("✅ Good audio levels detected! Your microphone is working well.")
            return True
            
    except Exception as e:
        print(f"❌ Audio level monitoring failed: {e}")
        return False


def list_microphones():
    try:
        return sr.Microphone.list_microphone_names() or []
    except Exception:
        return []
