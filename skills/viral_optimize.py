"""
skills/viral_optimize.py
------------------------
Viral Optimization module for the Autonomous Content Factory.
Fetches trending signals from free public sources, then uses qwen2.5:7b
to generate high-CTR titles, SEO descriptions, hashtags, and retention hooks.

STANDALONE USAGE:
    python skills/viral_optimize.py --niche entrepreneurship

REQUIREMENTS:
    pip install requests beautifulsoup4
"""

import os
import sys
import json
import time
import argparse
import hashlib
import re
import logging
from datetime import datetime
from typing import Optional

#  project root on path 
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

#  proxy / no-proxy enforcement 
os.environ.setdefault("HTTP_PROXY",  "http://172.30.10.10:3128")
os.environ.setdefault("HTTPS_PROXY", "http://172.30.10.10:3128")
os.environ["NO_PROXY"]  = "localhost,127.0.0.1"
os.environ["no_proxy"]  = "localhost,127.0.0.1"

PROXY_URL  = "http://172.30.10.10:3128"
PROXIES    = {"http": PROXY_URL, "https": PROXY_URL}

#  cache directory 
CACHE_DIR  = os.path.join(PROJECT_ROOT, "logs", "viral_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

#  logger 
logger = logging.getLogger("viral_optimize")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(asctime)s [VIRAL] %(message)s", "%H:%M:%S"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


# 
# SECTION 1 -- TRENDING RESEARCH
# 

def _cache_path(niche: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    key   = hashlib.md5(f"{niche}{today}".encode()).hexdigest()[:12]
    return os.path.join(CACHE_DIR, f"trending_{key}.json")


def _load_cache(niche: str) -> Optional[dict]:
    path = _cache_path(niche)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"[Cache] Loaded daily trending cache for niche: {niche}")
            return data
        except Exception:
            pass
    return None


def _save_cache(niche: str, data: dict):
    path = _cache_path(niche)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[Cache] Saved trending cache -> {path}")
    except Exception as e:
        logger.warning(f"[Cache] Could not save cache: {e}")


def _fetch_youtube_suggest(keyword: str) -> list:
    """YouTube autocomplete/suggest API -- no auth needed."""
    try:
        import requests
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "ds": "yt", "q": keyword}
        r = requests.get(url, params=params, proxies=PROXIES, timeout=8)
        if r.status_code == 200:
            suggestions = r.json()[1]
            logger.info(f"[YouTube-Suggest]  got {len(suggestions)} suggestions for '{keyword}'")
            return [s.strip() for s in suggestions if s.strip()]
    except Exception as e:
        logger.warning(f"[YouTube-Suggest]  skipped: {e}")
    return []


def _fetch_google_trends(keyword: str) -> list:
    """Google Trends related queries (unofficial dailytrends endpoint)."""
    try:
        import requests
        # Related topics via suggest
        url = "https://trends.google.com/trends/api/autocomplete"
        params = {"hl": "en-US", "tz": "-300", "q": keyword}
        r = requests.get(url, params=params, proxies=PROXIES, timeout=8)
        if r.status_code == 200:
            raw = r.text
            # Strip the JSONP-style prefix ")]}',"
            raw = re.sub(r"^\)\]\}',?", "", raw.strip())
            data = json.loads(raw)
            terms = []
            for item in data.get("default", {}).get("topics", [])[:10]:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("mid", "")
                    if title:
                        terms.append(title.strip())
            logger.info(f"[Google-Trends]  got {len(terms)} related topics for '{keyword}'")
            return terms
    except Exception as e:
        logger.warning(f"[Google-Trends]  skipped: {e}")
    return []


def _fetch_reddit_hot(subreddits: list) -> list:
    """Reddit JSON API -- hot posts titles."""
    try:
        import requests
        keywords = []
        headers  = {"User-Agent": "viral-optimizer/1.0"}
        for sub in subreddits[:3]:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            r   = requests.get(url, headers=headers, proxies=PROXIES, timeout=10)
            if r.status_code == 200:
                posts = r.json().get("data", {}).get("children", [])
                for p in posts:
                    title = p.get("data", {}).get("title", "")
                    if title:
                        keywords.append(title[:80])
                logger.info(f"[Reddit-{sub}]  got {len(posts)} hot posts")
            else:
                logger.warning(f"[Reddit-{sub}]  HTTP {r.status_code}")
            time.sleep(0.5)
        return keywords
    except Exception as e:
        logger.warning(f"[Reddit]  skipped: {e}")
    return []


def _fetch_hashtag_suggestions(keyword: str) -> list:
    """Hashtagify-style: pull from Instagram explore or fallback to Google suggest."""
    try:
        import requests
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client": "firefox", "q": f"#{keyword} hashtags 2024"}
        r = requests.get(url, params=params, proxies=PROXIES, timeout=8)
        if r.status_code == 200:
            suggestions = r.json()[1]
            # Extract hashtag-style keywords
            raw_tags = []
            for s in suggestions:
                words = re.findall(r"\b\w+\b", s.lower())
                raw_tags.extend(words)
            logger.info(f"[Hashtag-Suggest]  extracted hashtag signals for '{keyword}'")
            return list(set(raw_tags))[:20]
    except Exception as e:
        logger.warning(f"[Hashtag-Suggest]  skipped: {e}")
    return []


def _extract_keywords_from_titles(titles: list) -> list:
    """Simple NLP-free keyword extraction from a list of titles."""
    stop_words = {
        "the","a","an","and","or","but","in","on","at","to","for","of","with",
        "is","are","was","were","be","been","being","have","has","had","do","does",
        "did","will","would","could","should","may","might","shall","can","not",
        "from","by","as","into","through","during","before","after","above","below",
        "i","you","he","she","it","we","they","this","that","these","those","my",
        "your","his","her","our","their","what","which","who","how","when","where",
        "why","all","each","every","both","few","more","most","other","some","such",
        "no","nor","so","yet","both","either","neither","once","here","there","just",
        "about","up","out","if","then","because","so","though","while","after","since"
    }
    freq = {}
    for title in titles:
        words = re.findall(r"\b[a-zA-Z]{3,}\b", title.lower())
        for w in words:
            if w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
    # Sort by frequency descending
    sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in sorted_kw[:30]]


def trending_research(niche: str, force_refresh: bool = False) -> dict:
    """
    Fetch trending signals from free public sources.
    Returns a dict with keys: keywords, reddit_titles, hashtag_signals, sources_used.
    Results are cached daily per niche.
    """
    if not force_refresh:
        cached = _load_cache(niche)
        if cached:
            return cached

    logger.info(f"[Trending] Starting fresh research for niche: '{niche}'")

    # Seed keywords from niche
    seed_keywords = [
        niche,
        "startup success",
        "entrepreneurship tips",
        "business growth",
        "make money",
        "financial freedom",
        "side hustle",
        "passive income"
    ]

    sources_used  = []
    all_titles    = []
    all_keywords  = []
    hashtag_sigs  = []

    # 1. YouTube autocomplete
    for seed in seed_keywords[:4]:
        suggestions = _fetch_youtube_suggest(seed)
        if suggestions:
            all_titles.extend(suggestions)
            sources_used.append(f"youtube_suggest:{seed}")
        time.sleep(0.3)

    # 2. Google Trends autocomplete
    for seed in seed_keywords[:3]:
        terms = _fetch_google_trends(seed)
        if terms:
            all_keywords.extend(terms)
            sources_used.append(f"google_trends:{seed}")
        time.sleep(0.3)

    # 3. Reddit hot posts
    reddit_titles = _fetch_reddit_hot(["Entrepreneur", "startups", "smallbusiness", "financialindependence"])
    if reddit_titles:
        all_titles.extend(reddit_titles)
        sources_used.append("reddit_hot")

    # 4. Hashtag suggestions
    for seed in seed_keywords[:3]:
        tags = _fetch_hashtag_suggestions(seed)
        hashtag_sigs.extend(tags)
        if tags:
            sources_used.append(f"hashtag_suggest:{seed}")
        time.sleep(0.3)

    # 5. Extract keywords from all collected titles
    extracted = _extract_keywords_from_titles(all_titles + all_keywords)

    # Combine and deduplicate all keywords
    final_keywords = list(dict.fromkeys(extracted + all_keywords))[:40]

    result = {
        "niche": niche,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "keywords": final_keywords,
        "reddit_titles": reddit_titles[:15],
        "hashtag_signals": list(set(hashtag_sigs))[:30],
        "sources_used": sources_used,
        "fetched_at": datetime.now().isoformat()
    }

    _save_cache(niche, result)
    logger.info(f"[Trending] Research complete. Sources: {sources_used}")
    logger.info(f"[Trending] Top keywords: {final_keywords[:10]}")
    return result


# 
# SECTION 2 -- OLLAMA LLM HELPERS
# 

def _call_ollama(prompt: str, system: str = "", max_tokens: int = 400) -> str:
    """Call local Ollama qwen2.5:7b, bypassing proxy via urllib."""
    import urllib.request as ureq
    payload = {
        "model": "qwen2.5:7b",
        "messages": [
            {"role": "system", "content": system or "You are an expert viral social media content strategist."},
            {"role": "user",   "content": prompt}
        ],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }
    try:
        req = ureq.Request(
            "http://localhost:11434/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with ureq.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"].strip()
            # Strip <think> blocks if any
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            return text
    except Exception as e:
        logger.error(f"[Ollama] Call failed: {e}")
        return ""


def _parse_numbered_list(text: str) -> list:
    """Extract items from a numbered/bulleted list in LLM output."""
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove leading numbering / bullets
        cleaned = re.sub(r"^[\d]+[\.\)]\s*", "", line)
        cleaned = re.sub(r"^[-**]\s*", "", cleaned).strip()
        # Remove bold markdown
        cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
        if cleaned:
            lines.append(cleaned)
    return lines


# 
# SECTION 3 -- VIRAL TITLE
# 

PLATFORM_TITLE_RULES = {
    "youtube": "YouTube Shorts (under 60 chars, curiosity-gap, starts with number or power word, no clickbait)",
    "youtube_shorts": "YouTube Shorts (under 60 chars, curiosity-gap, starts with number or power word, no clickbait)",
    "tiktok":  "TikTok (punchy, under 50 chars, hooks with 'POV:' or 'No one tells you...' style)",
    "instagram": "Instagram Reels (under 55 chars, emotional, aspirational, relatable)",
    "reels":   "Instagram Reels (under 55 chars, emotional, aspirational, relatable)",
    "facebook": "Facebook (question or story-based, 60-90 chars, triggers curiosity or emotion)",
    "linkedin": "LinkedIn (professional insight framing, data-driven or story-driven, 60-100 chars)"
}


def viral_title(topic: str, platform: str, trending_keywords: list = None) -> str:
    """
    Generate 3-5 viral title options and pick the best one.
    Returns a single best title string.
    """
    kw_hint = ""
    if trending_keywords:
        kw_hint = f"\nIncorporate 1-2 of these trending keywords naturally: {', '.join(trending_keywords[:8])}"

    rules = PLATFORM_TITLE_RULES.get(platform.lower(), PLATFORM_TITLE_RULES["youtube"])

    prompt = f"""Generate 5 viral, high-CTR titles for a {rules} about:
TOPIC: {topic}
{kw_hint}

Rules:
- Use curiosity gaps, power words, numbers, or strong emotional hooks
- Each title must be UNIQUE in approach (question, number, contrast, story, challenge)
- No generic or boring titles
- Do NOT use quotation marks around titles
- Output ONLY a numbered list of 5 titles, nothing else

Titles:"""

    raw = _call_ollama(prompt)
    titles = _parse_numbered_list(raw)

    if not titles:
        # Fallback
        return f"The {topic} Strategy That Changed Everything"

    # Score and pick best: prefer titles with numbers, power words, shorter length
    power_words = {"secret","hidden","mistake","why","never","always","stop","best","worst",
                   "hack","trick","truth","finally","proven","simple","step","instantly","fast"}

    def score(t):
        t_lower = t.lower()
        s = 0
        if any(c.isdigit() for c in t):              s += 3
        if any(pw in t_lower for pw in power_words): s += 2
        if t.endswith("?"):                           s += 1
        if 30 <= len(t) <= 65:                       s += 2
        return s

    best = max(titles, key=score)
    logger.info(f"[viral_title] [{platform}] '{topic}' -> '{best}' (from {len(titles)} options)")
    return best


# 
# SECTION 4 -- VIRAL DESCRIPTION
# 

PLATFORM_DESC_RULES = {
    "youtube":       "YouTube video description: 200-300 words, start with a hook sentence, weave in 5-8 SEO keywords naturally, add timestamps section header, end with CTA to subscribe + comment",
    "youtube_shorts":"YouTube Shorts description: 80-120 words, hook + keywords + follow CTA",
    "tiktok":        "TikTok caption: 150 chars max, hook + 1 insight + CTA",
    "instagram":     "Instagram Reels caption: 100-150 words, hook line, story/insight, line breaks for readability, CTA to save/share, then hashtags on separate line",
    "reels":         "Instagram Reels caption: 100-150 words, hook line, story/insight, line breaks for readability, CTA to save/share",
    "facebook":      "Facebook post description: 80-150 words, conversational tone, hook question, value insight, CTA to comment",
    "linkedin":      "LinkedIn post: 150-250 words, professional hook, 3 key insights as short paragraphs, CTA to connect/share, no hashtags in body"
}


def viral_description(topic: str, platform: str, trending_keywords: list = None) -> str:
    """Generate an SEO-rich viral description for a platform."""
    kw_hint = ""
    if trending_keywords:
        kw_hint = f"\nNaturally incorporate these trending SEO keywords (don't force them): {', '.join(trending_keywords[:6])}"

    rules = PLATFORM_DESC_RULES.get(platform.lower(), PLATFORM_DESC_RULES["youtube"])

    prompt = f"""Write a {rules} for content about:
TOPIC: {topic}
{kw_hint}

Requirements:
- First line is a HOOK (bold claim, surprising stat, or provocative question)
- Weave in keywords naturally -- never keyword-stuff
- End with a clear CTA
- Output ONLY the description text, ready to copy-paste

Description:"""

    desc = _call_ollama(prompt, max_tokens=350)
    if not desc:
        desc = f"Discover the secrets behind {topic}. Watch till the end -- this changes everything. \n\nFollow for daily business insights!"
    logger.info(f"[viral_desc] [{platform}] Generated {len(desc)} chars for '{topic}'")
    return desc


# 
# SECTION 5 -- VIRAL HASHTAGS
# 

# Platform hashtag count targets
HASHTAG_COUNTS = {
    "youtube":        (3, 5),
    "youtube_shorts": (3, 5),
    "tiktok":         (4, 6),
    "instagram":      (15, 22),
    "reels":          (15, 22),
    "facebook":       (3, 5),
    "linkedin":       (3, 5)
}

# Base high-volume hashtags per niche
NICHE_BASE_TAGS = {
    "entrepreneurship": [
        "#entrepreneurship","#entrepreneur","#business","#startup","#success",
        "#motivation","#mindset","#money","#investing","#finance",
        "#sidehustle","#passiveincome","#wealth","#hustle","#grind"
    ]
}


def viral_hashtags(topic: str, platform: str, trending_keywords: list = None,
                   niche: str = "entrepreneurship") -> list:
    """
    Generate platform-appropriate hashtag set.
    Returns a list of hashtag strings.
    """
    min_count, max_count = HASHTAG_COUNTS.get(platform.lower(), (5, 10))

    kw_hint = ""
    if trending_keywords:
        kw_hint = f"\nBase some hashtags on these trending signals: {', '.join(trending_keywords[:8])}"

    prompt = f"""Generate a hashtag set for {platform} content about: {topic}
Niche: entrepreneurship / startups / business / money mindset
{kw_hint}

Rules:
- Mix: 2-3 high-volume (#entrepreneur, #startup) + 3-4 niche-specific + 2-3 trending/topic-specific
- Target count: {min_count} to {max_count} hashtags total
- All must start with #
- Output ONLY hashtags separated by spaces, one line, nothing else

Hashtags:"""

    raw = _call_ollama(prompt, max_tokens=100)
    
    # Extract all hashtags
    tags = re.findall(r"#\w+", raw)
    
    # Supplement with base tags if too few
    if len(tags) < min_count:
        base = NICHE_BASE_TAGS.get(niche.lower(), NICHE_BASE_TAGS["entrepreneurship"])
        for t in base:
            if t not in tags:
                tags.append(t)
            if len(tags) >= min_count:
                break

    # Trim to platform max
    tags = tags[:max_count]

    logger.info(f"[viral_hashtags] [{platform}] {len(tags)} hashtags for '{topic}'")
    return tags


# 
# SECTION 6 -- VIRAL HOOK (first 2 seconds of video script)
# 

def viral_hook(topic: str, trending_keywords: list = None) -> str:
    """
    Generate a 1-line retention hook for the first 2 seconds of the video script.
    """
    kw_hint = ""
    if trending_keywords:
        kw_hint = f" (weave in one of these if natural: {', '.join(trending_keywords[:4])})"

    prompt = f"""Write a single-sentence video HOOK for the first 2 seconds of a short video about: {topic}
{kw_hint}

Rules:
- Maximum 15 words
- Must create immediate curiosity or FOMO
- Start with "Did you know", "Stop if you...", "The #1 reason why...", "Nobody tells you...", or similar
- Output ONLY the hook sentence, nothing else

Hook:"""

    hook = _call_ollama(prompt, max_tokens=50).strip()
    # Clean up any trailing punctuation issues
    hook = re.sub(r"\s+", " ", hook).strip()
    if not hook:
        hook = f"Stop everything -- this {topic} secret changes your entire approach."
    logger.info(f"[viral_hook] Hook: '{hook}'")
    return hook


# 
# SECTION 7 -- FULL VIRAL PACKAGE (one call for all)
# 

def get_viral_package(topic: str, niche: str = "entrepreneurship",
                      platforms: list = None,
                      trending_data: dict = None) -> dict:
    """
    Returns a complete viral metadata package for a given topic.
    trending_data can be passed in to avoid re-fetching.
    """
    if platforms is None:
        platforms = ["youtube_shorts", "instagram", "facebook", "linkedin", "tiktok"]

    if trending_data is None:
        trending_data = trending_research(niche)

    kw = trending_data.get("keywords", [])

    hook = viral_hook(topic, kw)

    package = {
        "topic": topic,
        "hook":  hook,
        "trending_keywords_used": kw[:10],
        "platforms": {}
    }

    for platform in platforms:
        title  = viral_title(topic, platform, kw)
        desc   = viral_description(topic, platform, kw)
        tags   = viral_hashtags(topic, platform, kw, niche)
        package["platforms"][platform] = {
            "title":       title,
            "description": desc,
            "hashtags":    tags
        }

    return package


# 
# SECTION 8 -- STANDALONE CLI COMMAND
# 

def _cli_run(niche: str, force_refresh: bool = False):
    """Standalone CLI: print today's trending keywords + 10 viral ideas + hashtags."""
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("\n" + "="*70)
    print(f"   VIRAL INTELLIGENCE REPORT -- {niche.upper()}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    # 1. Trending research
    print("\n Fetching trending signals...")
    data = trending_research(niche, force_refresh=force_refresh)

    print(f"\n Sources used: {len(data['sources_used'])}")
    for src in data["sources_used"]:
        print(f"   * {src}")

    print(f"\n TOP TRENDING KEYWORDS ({len(data['keywords'])} found):")
    for i, kw in enumerate(data["keywords"][:15], 1):
        print(f"   {i:>2}. {kw}")

    print(f"\n🧵 HOT REDDIT TOPICS (r/Entrepreneur, r/startups):")
    for title in data.get("reddit_titles", [])[:5]:
        print(f"   * {title}")

    # 2. 10 viral title ideas across platforms
    print("\n" + "-"*70)
    print(" 10 READY-TO-USE VIRAL TITLE IDEAS")
    print("-"*70)
    seed_topics = [
        "making your first $10K online",
        "startup mistakes that kill businesses",
        "passive income strategies that actually work",
        "building wealth from scratch"
    ]
    platforms_cycle = ["youtube_shorts", "instagram", "tiktok", "linkedin", "facebook",
                       "youtube_shorts", "instagram", "tiktok", "linkedin", "facebook"]
    count = 1
    for i, topic in enumerate(seed_topics):
        plat = platforms_cycle[i]
        title = viral_title(topic, plat, data["keywords"])
        print(f"   {count:>2}. [{plat.upper():>15}] {title}")
        count += 1
        if count > 10:
            break
    # Fill remaining if needed
    for i in range(count, 11):
        topic = seed_topics[i % len(seed_topics)]
        plat  = platforms_cycle[i % len(platforms_cycle)]
        title = viral_title(f"{niche} tip #{i}", plat, data["keywords"])
        print(f"   {i:>2}. [{plat.upper():>15}] {title}")

    # 3. Hashtag sets
    print("\n" + "-"*70)
    print("  HASHTAG SETS PER PLATFORM")
    print("-"*70)
    for platform in ["youtube_shorts", "instagram", "tiktok", "linkedin"]:
        tags = viral_hashtags(niche, platform, data["keywords"], niche)
        print(f"\n   {platform.upper()}:")
        print("   " + " ".join(tags))

    # 4. Sample hook
    print("\n" + "-"*70)
    print(" SAMPLE RETENTION HOOKS")
    print("-"*70)
    for topic in seed_topics[:3]:
        hook = viral_hook(topic, data["keywords"])
        print(f"   * \"{hook}\"")

    print("\n" + "="*70)
    print("  Done! Run again tomorrow for fresh trending data.")
    print("="*70 + "\n")


# 
# ENTRY POINT
# 

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Viral Optimization CLI")
    parser.add_argument("--niche", type=str, default="entrepreneurship",
                        help="Niche / topic area to research")
    parser.add_argument("--force-refresh", action="store_true",
                        help="Bypass daily cache and force fresh fetch")
    args = parser.parse_args()

    # Set up console logging for standalone mode
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])

    _cli_run(args.niche, force_refresh=args.force_refresh)
