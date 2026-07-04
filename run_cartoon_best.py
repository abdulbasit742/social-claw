"""
BEST VERSION cartoon pipeline:
- Microsoft Zira voice (female, energetic)
- Background music (random from local songs)
- BGM volume 0.15 (subtle, voice stays clear)
- 3s clip cuts (more dynamic than 4s)
- Yellow subtitles with rounded background
- Better cartoon search terms targeting actual animation clips
- Fade transitions between clips
"""
import os, sys, subprocess

ROOT   = r"C:\Users\absh5\MoneyPrinterTurbo"
PYTHON = os.path.join(ROOT, "venv", "Scripts", "python.exe")
CLI    = os.path.join(ROOT, "cli.py")

with open(os.path.join(ROOT, "cartoon_script.txt"), "r", encoding="utf-8-sig") as f:
    script = f.read().strip().replace("\r\n", " ").replace("\n", " ")

print(f"Script ({len(script.split())} words): {script[:80]}...")
print("Upgrades: Zira voice | BGM music | 3s clips | rounded subtitles | fade transitions")

env = os.environ.copy()
env["HTTP_PROXY"]  = "http://172.30.10.10:3128"
env["HTTPS_PROXY"] = "http://172.30.10.10:3128"
env["NO_PROXY"]    = "localhost,127.0.0.1"
env["no_proxy"]    = "localhost,127.0.0.1"
env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

cmd = [
    PYTHON, CLI,
    "--video-subject",      "cartoon cat mouse chase funny animation",
    "--video-script",       script,
    "--video-terms",        "cartoon animation,2D animation,funny cat video,animated characters,cartoon running",
    "--video-aspect",       "9:16",
    "--video-source",       "pexels",
    "--custom-audio-file",  os.path.join(ROOT, "voice.wav"),
    "--subtitle-enabled",
    "--font-name",          "MicrosoftYaHeiBold.ttc",
    "--subtitle-position",  "bottom",
    "--text-fore-color",    "#FFFF00",           # bright yellow
    "--font-size",          "65",                # bigger = more punch
    "--subtitle-background-enabled",
    "--rounded-subtitle-background",             # pill-shaped background
    "--bgm-type",           "random",            # 🎵 background music!
    "--bgm-volume",         "0.12",              # subtle under voice
    "--voice-volume",       "2.0",               # voice louder than BGM
    "--video-clip-duration","3",                 # fast 3s cuts
    "--video-transition-mode", "fade-in",        # smooth fades
    "--video-concat-mode",  "random",
    "--video-count",        "1",
]

print("\nLaunching BEST VERSION pipeline...")
result = subprocess.run(cmd, cwd=ROOT, env=env,
                        stdout=sys.stdout, stderr=sys.stderr,
                        text=True, encoding="utf-8", errors="replace")
sys.exit(result.returncode)
