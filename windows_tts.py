#!/usr/bin/env python3
"""
Windows TTS using SAPI (Speech API)
This works better in subprocess environments
"""
import os
import subprocess
from console_utils import safe_print

def speak_windows_sapi(text):
    """Use Windows SAPI to speak text via PowerShell"""
    try:
        safe_print(f"🔊 [SAPI] Speaking: '{text}'")
        
        # Escape quotes and special characters for PowerShell
        escaped_text = text.replace("'", "''").replace('"', '""')
        
        # Use PowerShell with Windows Speech API
        powershell_cmd = f'''
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = 0
$speak.Volume = 100
$speak.Speak("{escaped_text}")
$speak.Dispose()
'''
        
        # Run PowerShell command
        result = subprocess.run([
            'powershell', '-WindowStyle', 'Hidden', '-Command', powershell_cmd
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            safe_print("✅ [SAPI] Speech completed successfully")
            return True
        else:
            safe_print(f"❌ [SAPI] Speech failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        safe_print("⏰ [SAPI] Speech timeout")
        return False
    except Exception as e:
        safe_print(f"❌ [SAPI] Error: {e}")
        return False

def speak_windows_narrator(text):
    """Use Windows built-in narrator command"""
    try:
        safe_print(f"🔊 [NARRATOR] Speaking: '{text}'")
        
        # Create a temporary file with the text
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(text)
            temp_file = f.name
        
        # Use Windows narrator
        result = subprocess.run([
            'narrator', '/file', temp_file
        ], capture_output=True, timeout=10)
        
        # Clean up
        try:
            os.unlink(temp_file)
        except:
            pass
            
        if result.returncode == 0:
            safe_print("✅ [NARRATOR] Speech completed")
            return True
        else:
            safe_print(f"❌ [NARRATOR] Failed: {result.stderr}")
            return False
            
    except Exception as e:
        safe_print(f"❌ [NARRATOR] Error: {e}")
        return False

def speak_windows_command(text):
    """Use Windows command line TTS"""
    try:
        safe_print(f"🔊 [CMD] Speaking via command line: '{text}'")
        
        # Create VBScript for TTS
        import tempfile
        vbs_content = f'''
Set objVoice = CreateObject("SAPI.SpVoice")
objVoice.Rate = 0
objVoice.Volume = 100
objVoice.Speak "{text.replace('"', '""')}"
Set objVoice = Nothing
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vbs', delete=False) as f:
            f.write(vbs_content)
            vbs_file = f.name
        
        # Run VBScript
        result = subprocess.run([
            'cscript', '//NoLogo', vbs_file
        ], capture_output=True, timeout=30, cwd=os.path.dirname(vbs_file))
        
        # Clean up
        try:
            os.unlink(vbs_file)
        except:
            pass
            
        if result.returncode == 0:
            safe_print("✅ [CMD] Speech completed successfully")
            return True
        else:
            safe_print(f"❌ [CMD] Speech failed: {result.stderr}")
            return False
            
    except Exception as e:
        safe_print(f"❌ [CMD] Error: {e}")
        return False

def speak_subprocess_safe(text):
    """Try multiple Windows TTS methods until one works"""
    safe_print(f"🎯 [SAFE] Attempting to speak: '{text[:50]}...'")
    
    # Try methods in order of preference
    methods = [
        ("Windows SAPI (PowerShell)", speak_windows_sapi),
        ("Windows Command TTS", speak_windows_command),
        ("Windows Narrator", speak_windows_narrator),
    ]
    
    for method_name, method_func in methods:
        safe_print(f"🔄 [SAFE] Trying {method_name}...")
        try:
            if method_func(text):
                safe_print(f"✅ [SAFE] Success with {method_name}")
                return True
        except Exception as e:
            safe_print(f"❌ [SAFE] {method_name} failed: {e}")
            continue
    
    safe_print("❌ [SAFE] All TTS methods failed")
    return False

if __name__ == "__main__":
    # Test the TTS methods
    test_text = "This is a test of Windows TTS from subprocess"
    speak_subprocess_safe(test_text)