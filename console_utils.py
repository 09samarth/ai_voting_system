# Windows console compatibility utilities
import sys

def safe_print(text):
    """Safely print text with emoji fallbacks for Windows compatibility"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace common emojis with ASCII alternatives for Windows compatibility
        emoji_map = {
            '🎤': '[MIC]',
            '🤖': '[BOT]',
            '❌': '[X]',
            '✅': '[OK]',
            '🔧': '[TOOL]',
            '🔄': '[LOADING]',
            '⚠️': '[WARN]',
            '🗣️': '[VOICE]',
            '🏁': '[DONE]',
            '🛑': '[STOP]',
            '🌐': '[WEB]',
            '📡': '[SIGNAL]',
            '⏰': '[TIME]',
            '🔍': '[SEARCH]',
            '📊': '[CHART]',
            '👋': '[WAVE]',
            '█': '#',
            '░': '-',
            '🔊': '[SPEAKER]',
            '🎯': '[TARGET]',
            '💡': '[IDEA]',
            '⭐': '[STAR]',
            '🚀': '[ROCKET]',
            '📝': '[NOTE]',
            '🎵': '[MUSIC]'
        }
        safe_text = text
        for emoji, replacement in emoji_map.items():
            safe_text = safe_text.replace(emoji, replacement)
        try:
            print(safe_text.encode('ascii', 'replace').decode('ascii'))
        except:
            print(safe_text.encode('utf-8', 'replace').decode('utf-8', 'replace'))

def enable_utf8_console():
    """Attempt to enable UTF-8 support on Windows console"""
    try:
        # Try to set console to UTF-8 mode
        if sys.platform == 'win32':
            import subprocess
            subprocess.run(['chcp', '65001'], shell=True, capture_output=True)
    except:
        pass