"""
Generate voice.wav from voice_script.txt using pyttsx3 (Windows SAPI - fully offline).
"""
import os
import sys

# Force UTF-8 output to avoid charmap errors on Windows console
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

script_path = os.path.join(os.path.dirname(__file__), "voice_script.txt")
output_path = os.path.join(os.path.dirname(__file__), "voice.wav")

# Read with utf-8-sig to strip BOM if present
with open(script_path, "r", encoding="utf-8-sig") as f:
    text = f.read().strip()

word_count = len(text.split())
print(f"Script text ({word_count} words):")
print(repr(text[:80]) + "...")
print()

import pyttsx3

engine = pyttsx3.init()

# Set rate ~165 wpm
engine.setProperty("rate", 165)
# Set volume
engine.setProperty("volume", 0.95)

# List available voices and pick an English one
voices = engine.getProperty("voices")
print("Available voices:")
for i, v in enumerate(voices):
    print(f"  [{i}] {v.id} | {v.name} | {v.languages}")

# Pick English voice if available
english_voice = None
for v in voices:
    if "en" in (v.id or "").lower() or "en" in str(v.languages).lower() or "english" in (v.name or "").lower():
        english_voice = v.id
        print(f"Selected voice: {v.name}")
        break

if english_voice:
    engine.setProperty("voice", english_voice)

engine.save_to_file(text, output_path)
engine.runAndWait()

# Verify
if os.path.isfile(output_path):
    size = os.path.getsize(output_path)
    print(f"\n✅ voice.wav created: {output_path}")
    print(f"   Size: {size:,} bytes ({size/1024:.1f} KB)")
    if size < 1000:
        print("❌ ERROR: File too small, TTS may have failed!")
        sys.exit(1)
else:
    print("❌ ERROR: voice.wav not created!")
    sys.exit(1)
