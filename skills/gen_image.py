import os
import sys
import argparse
import subprocess
import uuid

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Force working directory to project root
os.chdir(project_root)

from app.services.llm import _generate_response_core

def refine_visual_prompt(topic: str) -> str:
    print(f"[gen_image] Refining topic '{topic}' using Ollama...")
    prompt = (
        "You are an expert prompt engineer for FLUX.1 image generator.\n"
        "Generate a highly detailed, visually stunning prompt (1-3 sentences) suitable for an image. "
        "The theme should be entrepreneurship, startups, business mindset, motivation, or high-tech success. "
        "Keep it highly descriptive (textures, lighting, colors), but do not include metadata or camera specs.\n"
        f"Topic to expand: {topic}\n"
        "Return ONLY the refined prompt text. Do not wrap in quotes or add intro/outro text."
    )
    try:
        refined = _generate_response_core(prompt).strip()
        # Clean any accidental quotes
        if refined.startswith('"') and refined.endswith('"'):
            refined = refined[1:-1].strip()
        print(f"[gen_image] Refined Prompt: {refined}")
        return refined
    except Exception as e:
        print(f"[gen_image] Refinement failed: {e}. Using raw topic.")
        return topic

def gen_image(prompt: str, aspect: str = "1:1", output_path: str = None) -> str:
    # If output_path is not specified, generate a random one in storage/tasks
    if not output_path:
        task_id = str(uuid.uuid4())
        output_dir = os.path.join(project_root, "storage", "tasks", task_id)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "flux_image.png")
        
    refined_prompt = refine_visual_prompt(prompt)
    
    flux_dir = r"C:\Users\absh5\flux"
    flux_python = os.path.join(flux_dir, "venv", "Scripts", "python.exe")
    flux_script = os.path.join(flux_dir, "generate.py")
    
    cmd = [
        flux_python,
        flux_script,
        "--prompt", refined_prompt,
        "--aspect", aspect,
        "--output", output_path
    ]
    
    print(f"[gen_image] Invoking local FLUX generator script...")
    env = os.environ.copy()
    # Pass HTTP/HTTPS proxy to ensure diffusers/huggingface can fetch/validate cache if needed
    env["HTTP_PROXY"] = "http://172.30.10.10:3128"
    env["HTTPS_PROXY"] = "http://172.30.10.10:3128"
    
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")
    
    print(f"[gen_image] stdout:\n{result.stdout}")
    if result.stderr:
        print(f"[gen_image] stderr:\n{result.stderr}", file=sys.stderr)
        
    if result.returncode != 0:
        raise RuntimeError(f"Local FLUX generator failed with code {result.returncode}")
        
    if os.path.exists(output_path):
        print(f"[gen_image] Successfully generated image: {output_path}")
        return output_path
    else:
        raise FileNotFoundError("FLUX generated image not found at expected path")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Generate Visuals via Local FLUX.1")
    parser.add_argument("--prompt", required=True, help="Prompt or topic for image")
    parser.add_argument("--aspect", default="1:1", choices=["9:16", "16:9", "1:1", "4:5"], help="Aspect ratio")
    parser.add_argument("--output", default=None, help="Output file path (.png)")
    args = parser.parse_args()
    
    try:
        path = gen_image(args.prompt, args.aspect, args.output)
        print(f"RESULT_PATH:{path}")
    except Exception as ex:
        print(f"Error: {ex}", file=sys.stderr)
        sys.exit(1)
