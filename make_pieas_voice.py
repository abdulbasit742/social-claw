"""
Generate voice.wav for the PIEAS documentary using pyttsx3 (offline Windows SAPI).
Then verify duration is between 110-130 seconds using the stdlib wave module.
"""
import os
import sys
import wave as _wave
import subprocess

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_FILE = os.path.join(os.path.dirname(__file__), "pieas_script.txt")
OUTPUT_WAV  = os.path.join(os.path.dirname(__file__), "voice.wav")
TARGET_RATE = 165   # words per minute for pyttsx3
MIN_DUR = 110.0
MAX_DUR = 130.0

def read_script(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return f.read().strip()

def wav_duration(path):
    with _wave.open(path, "rb") as wf:
        frames = wf.getnframes()
        rate   = wf.getframerate()
        dur    = frames / float(rate)
        print(f"  WAV: {frames} frames @ {rate}Hz => {dur:.2f}s")
        return dur

def tts(text, output_path, rate=TARGET_RATE):
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", 0.95)

    voices = engine.getProperty("voices")
    for v in voices:
        if "en" in (v.id or "").lower() or "english" in (v.name or "").lower():
            engine.setProperty("voice", v.id)
            print(f"  Voice: {v.name}")
            break

    engine.save_to_file(text, output_path)
    engine.runAndWait()

# ── Step 1: read script ──────────────────────────────────────────────────────
script = read_script(SCRIPT_FILE)
word_count = len(script.split())
print(f"\n[1] Script loaded: {word_count} words")
print(f"    Estimated duration @ {TARGET_RATE} wpm: {word_count/TARGET_RATE*60:.1f}s\n")

# ── Step 2: generate audio ───────────────────────────────────────────────────
print(f"[2] Generating voice.wav (rate={TARGET_RATE})...")
tts(script, OUTPUT_WAV, rate=TARGET_RATE)

if not os.path.isfile(OUTPUT_WAV) or os.path.getsize(OUTPUT_WAV) < 1000:
    print("ERROR: voice.wav not created or too small!")
    sys.exit(1)

dur = wav_duration(OUTPUT_WAV)
print(f"\n[3] Duration check: {dur:.2f}s (target: {MIN_DUR}-{MAX_DUR}s)")

# ── Step 3: duration guard ───────────────────────────────────────────────────
if dur < MIN_DUR:
    # Too short — slow down rate
    needed_rate = int(word_count / (MIN_DUR / 60) * 0.97)
    print(f"    Too short! Retrying at rate={needed_rate}...")
    tts(script, OUTPUT_WAV, rate=needed_rate)
    dur = wav_duration(OUTPUT_WAV)
    print(f"    New duration: {dur:.2f}s")
elif dur > MAX_DUR:
    # Too long — speed up
    needed_rate = int(word_count / (MAX_DUR / 60) * 1.03)
    print(f"    Too long! Retrying at rate={needed_rate}...")
    tts(script, OUTPUT_WAV, rate=needed_rate)
    dur = wav_duration(OUTPUT_WAV)
    print(f"    New duration: {dur:.2f}s")

# ── Final check ──────────────────────────────────────────────────────────────
size = os.path.getsize(OUTPUT_WAV)
print(f"\n{'='*50}")
if MIN_DUR <= dur <= MAX_DUR:
    print(f"SUCCESS: voice.wav is {dur:.2f}s ({size:,} bytes)")
    print(f"  Path: {OUTPUT_WAV}")
else:
    print(f"WARNING: duration {dur:.2f}s is outside [{MIN_DUR},{MAX_DUR}]s")
    print(f"  Proceeding anyway — close enough for pipeline.")
    print(f"  Path: {OUTPUT_WAV}")
