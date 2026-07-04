import os
import sys
import argparse
import json
import uuid

# Ensure project root is in path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Force working directory to project root
os.chdir(project_root)

from app.services.llm import _generate_response_core
from skills.gen_image import gen_image

def make_post(topic: str, niche: str) -> dict:
    print(f"[make_post] Generating multi-platform captions and image prompt for '{topic}'...")
    
    prompt = (
        "You are an expert social media marketer for startups and entrepreneurship.\n"
        f"Niche: {niche}\n"
        f"Topic: {topic}\n\n"
        "Generate engaging post captions optimized for LinkedIn, Facebook, and Instagram, plus an image description prompt for FLUX.1:\n"
        "1. linkedin: Professional tone, hooks the reader, has clean paragraph breaks, provides key insight, includes a CTA (Call to Action), and 5-8 relevant hashtags.\n"
        "2. facebook: Engaging, clear value, includes emojis, has a CTA, and hashtags.\n"
        "3. instagram: Very punchy, uses emojis, calls to action, and includes hashtags.\n"
        "4. image_prompt: A detailed, visual description (1-2 sentences) representing the topic. Keep it conceptual and clean.\n\n"
        "Return ONLY a valid JSON object with the keys: 'linkedin', 'facebook', 'instagram', 'image_prompt'.\n"
        "Do not wrap in markdown tags like ```json. Return only raw JSON content."
    )
    
    response_text = ""
    parsed = {}
    for attempt in range(3):
        try:
            response_text = _generate_response_core(prompt).strip()
            # Clean JSON markdown if present
            if response_text.startswith("```"):
                # strip out lines starting with ```
                lines = response_text.splitlines()
                clean_lines = [l for l in lines if not l.strip().startswith("```")]
                response_text = "\n".join(clean_lines).strip()
            
            parsed = json.loads(response_text)
            if all(k in parsed for k in ['linkedin', 'facebook', 'instagram', 'image_prompt']):
                break
        except Exception as e:
            print(f"[make_post] JSON parse attempt {attempt+1} failed: {e}. Raw response: {response_text[:100]}...")
            
    if not parsed:
        # Fallback heuristic
        parsed = {
            "linkedin": f"Success mindset: {topic}. What are your thoughts on this? #business #startups #mindset",
            "facebook": f"Mindset shifts for {topic}! 🚀 Let's grow together. #entrepreneur",
            "instagram": f"Focus on {topic} today! 💡 #motivation",
            "image_prompt": f"A symbolic visual representation of {topic}, clean modern business style."
        }
        
    print(f"[make_post] Successfully generated captions.")
    
    # Generate the image using the FLUX model
    # We default to 1:1 aspect ratio for image feed posts
    task_id = str(uuid.uuid4())
    output_dir = os.path.join(project_root, "storage", "tasks", task_id)
    os.makedirs(output_dir, exist_ok=True)
    image_path = os.path.join(output_dir, "flux_post.png")
    
    img_prompt = parsed.get("image_prompt", topic)
    print(f"[make_post] Generating image via FLUX for prompt: {img_prompt}")
    
    try:
        gen_image(img_prompt, aspect="1:1", output_path=image_path)
    except Exception as img_err:
        print(f"[make_post] Image generation failed: {img_err}. Creating a fallback empty dummy image...")
        # Write 1-pixel fallback dummy JPG
        with open(image_path, "wb") as f:
            f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\x37\xff\xd9')
            
    result = {
        "captions": {
            "linkedin": parsed.get("linkedin"),
            "facebook": parsed.get("facebook"),
            "instagram": parsed.get("instagram")
        },
        "image_path": image_path
    }
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill: Create Social Media Text + Image Post")
    parser.add_argument("--topic", required=True, help="Topic for post")
    parser.add_argument("--niche", default="entrepreneurship, startups, business mindset", help="Niche domain")
    args = parser.parse_args()
    
    try:
        post_data = make_post(args.topic, args.niche)
        print(f"RESULT_JSON:{json.dumps(post_data)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
