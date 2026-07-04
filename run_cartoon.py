"""
Cartoon video pipeline launcher for MoneyPrinterTurbo.
Uses animation/cartoon stock footage from Pexels.
"""
import os, sys, subprocess

ROOT   = r"C:\Users\absh5\MoneyPrinterTurbo"
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
CLI    = os.path.join(ROOT, "cli.py")

with open(os.path.join(ROOT, "cartoon_script.txt"), "r", encoding="utf-8-sig") as f:
    script = f.read().strip().replace("\r\n", " ").replace("\n", " ")

print(f"Script ({len(script.split())} words): {script[:80]}...")

env = os.environ.copy()
env["HTTP_PROXY"]  = "http://172.30.10.10:3128"
env["HTTPS_PROXY"] = "http://172.30.10.10:3128"
env["NO_PROXY"]    = "localhost,127.0.0.1"
env["no_proxy"]    = "localhost,127.0.0.1"
env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

cmd = [
    PYTHON, CLI,
    "--video-subject",      "cartoon cat and mouse chase animation",
    "--video-script",       script,
    "--video-terms",        "cartoon animation,animated characters,funny cat,cute mouse,cartoon chase",
    "--video-aspect",       "9:16",
    "--video-source",       "pexels",
    "--custom-audio-file",  os.path.join(ROOT, "voice.wav"),
    "--subtitle-enabled",
    "--font-name",          "MicrosoftYaHeiBold.ttc",
    "--subtitle-position",  "bottom",
    "--text-fore-color",    "#FFFF00",          # bright yellow text for cartoon feel
    "--subtitle-background-enabled",
    "--video-clip-duration","4",                # shorter clips = more dynamic
    "--video-concat-mode",  "random",
    "--video-count",        "1",
]

print("Launching pipeline...")
result = subprocess.run(cmd, cwd=ROOT, env=env,
                        stdout=sys.stdout, stderr=sys.stderr,
                        text=True, encoding="utf-8", errors="replace")
sys.exit(result.returncode)
