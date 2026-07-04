"""
Launch MoneyPrinterTurbo CLI for the PIEAS documentary video.
Reads the script from file and passes it to cli.py to avoid shell quoting issues.
"""
import os
import sys
import subprocess

ROOT = r"C:\Users\absh5\MoneyPrinterTurbo"
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
CLI = os.path.join(ROOT, "cli.py")
SCRIPT_FILE = os.path.join(ROOT, "pieas_script.txt")
VOICE_WAV = os.path.join(ROOT, "voice.wav")

# Read script
with open(SCRIPT_FILE, "r", encoding="utf-8-sig") as f:
    script = f.read().strip().replace("\r\n", " ").replace("\n", " ")

print(f"Script: {len(script.split())} words")
print(f"Audio:  {VOICE_WAV}")
print(f"CLI:    {CLI}")
print()

env = os.environ.copy()
env["HTTP_PROXY"]  = "http://172.30.10.10:3128"
env["HTTPS_PROXY"] = "http://172.30.10.10:3128"
env["NO_PROXY"]    = "localhost,127.0.0.1"
env["no_proxy"]    = "localhost,127.0.0.1"
env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

cmd = [
    PYTHON, CLI,
    "--video-subject",      "PIEAS University documentary",
    "--video-script",       script,
    "--video-aspect",       "9:16",
    "--video-source",       "pexels",
    "--custom-audio-file",  VOICE_WAV,
    "--subtitle-enabled",
    "--font-name",          "MicrosoftYaHeiBold.ttc",
    "--subtitle-position",  "bottom",
    "--text-fore-color",    "#FFFFFF",
    "--subtitle-background-enabled",
    "--video-count",        "1",
    "--video-clip-duration","5",
]

print("Starting pipeline...")
result = subprocess.run(cmd, cwd=ROOT, env=env,
                        stdout=sys.stdout, stderr=sys.stderr,
                        text=True, encoding="utf-8", errors="replace")
sys.exit(result.returncode)
