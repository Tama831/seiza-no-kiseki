#!/usr/bin/env python3
"""星座の軌跡 — キャラクター肖像図版ジェネレータ v2 (方式B: 時代でメディア進化)
銅版画(AE480-1400) → 青焼き写真(AE1600-1950) → スキャン(AE2000+)。
全員「可愛げ・親しみやすさ」: 絵本的なやわらかい人物造形、顔は見せる(2026-06-12 たまさん指示)。
鍵は環境変数 GEMINI_API_KEY (コミットしない)。
usage: GEMINI_API_KEY=… python3 tools/gen_portraits.py [char_id …]
"""
import base64, json, os, sys, time, urllib.request

MODEL = "gemini-3-pro-image"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "portraits", "test")

# ---- 共通: 可愛げ・親しみ (全メディア共通の人物造形) ----
CHARM = (
    "The character is drawn with a gentle, approachable, contemporary storybook "
    "sensibility: soft rounded facial features, kind readable eyes, a calm warm "
    "expression, slightly stylized appealing proportions. The face is clearly visible "
    "and likable. NOT chibi, NOT glossy modern anime, no oversized sparkling eyes, "
    "no glamour. Worn clothes and tired-but-resilient warmth keep the quiet dignity "
    "of a war testimony. Single full-body figure, standing, slight three-quarter view, "
    "whole figure inside the frame with generous margins. Absolutely no text, no "
    "letters, no numbers, no watermark."
)

# ---- メディア別テンプレート (方式B) ----
MEDIA = {
    "engraving": (
        "Medium: an antique cyanotype blueprint plate combined with fine copper-"
        "engraving line work. Deep prussian-blue paper ground (dark indigo like #0e2647), "
        "the figure rendered in pale white-blue linework with soft halation, like light "
        "fixed into photographic paper. Fine archival hatching, weathered print texture, "
        "subtle darker-blue plate border of an archaeological documentation plate."
    ),
    "photo": (
        "Medium: a hand-drawn storybook illustration (soft pencil-and-wash character "
        "art, gently stylized, warm and approachable — absolutely NOT photorealistic, "
        "NOT a real photograph) that has been printed as a 19th-century style cyanotype "
        "photographic print: prussian-blue monochrome, soft focus edges, gentle "
        "halation, paper grain, slightly faded corners, hand-mounted with pale corner "
        "tabs on a deep blue album page."
    ),
    "scan_amber": (
        "Medium: a digitized scan of a hand-drawn ink figure study on salvaged paper "
        "from a wanderer's field notebook. Warm amber-tinged paper, frayed page edges, "
        "pencil construction lines, small hand-drawn margin notes as abstract scribbles "
        "(no real letters), quiet archival mood; the page rests on a deep prussian-blue "
        "background."
    ),
    "scan_cyan": (
        "Medium: a digitized frame from a virtual data layer. The figure appears as a "
        "pale cyan-glowing volumetric scan on a deep indigo-blue ground, with faint "
        "horizontal scanlines, a soft digital halation, thin glitch traces at the "
        "edges, and a subtle grid far in the background. Gentle, melancholic, not "
        "aggressive cyberpunk."
    ),
}

CHARS = {
    "char_01": ("aen", "engraving",
        "A young farm conscript man of an early-medieval agrarian village (fantasy "
        "world, year 480): rough hand-woven tunic and leg wraps, a simple slightly "
        "ill-fitting leather chest piece, carrying a farming hoe over his shoulder and "
        "a small cloth bundle. Lean, work-worn, a determined but gentle young face. "
        "A few wheat stalks at his feet."),
    "char_02": ("solea", "engraving",
        "A young desert nomad woman (fantasy world, year 495): layered desert robes "
        "and a long head cloth against sand wind, woven sash, a leather water skin and "
        "a shepherd's staff. Standing on a low dune, hem moving in wind, a calm gentle "
        "gaze and a quiet protective warmth, as if watching over children just outside "
        "the frame. Clean simple background, no other figures."),
    "char_04": ("lyan", "engraving",
        "A young court lady-scribe of an east-asian style imperial palace (fantasy "
        "world, year 1350): layered silk court robes with wide sleeves, hair pinned up "
        "simply, holding a writing brush and a bound bundle of records. Composed soft "
        "features, an intelligent kind expression, standing on a stone palace floor."),
    "char_06": ("karin", "photo",
        "A young mother of a small forest tribe (fantasy world, year 1680): practical "
        "woven-fiber and hide clothing, a woven carrying band across the chest, holding "
        "the hand of her small four-year-old son who peeks out shyly from behind her. "
        "Both faces visible and soft; she is weary but steady, with a faint reassuring "
        "smile. Standing among tall young trees."),
    "char_35": ("nagi", "scan_amber",
        "An androgynous wandering ruin-surveyor in a far, quiet, fallen future (year "
        "2163, low-tech salvage world, no machines): layered patched traveling clothes "
        "sewn from salvaged cloth, a heavy pack with a rolled blanket, a walking staff, "
        "an open field notebook in one hand. Dust-worn boots, a light curious "
        "expression, standing amid faintly sketched ruin outlines."),
    "char_22": ("rai", "scan_cyan",
        "A thin androgynous person in their late twenties who lives alone in a ruined "
        "concrete fortress and connects to a virtual data city (year 2157): a thin worn "
        "jacket over layered shabby clothes, a slender cable running from a small port "
        "at the back of the neck down toward a salvaged reclining chair hinted beside "
        "them. Tired but soft hopeful face, calm half-smile, faint cyan light reflecting "
        "on their cheek."),
}

def gen(cid, slug, media, desc, key):
    prompt = MEDIA[media] + "\n\n" + CHARM + "\n\nSubject: " + desc
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": "3:4"},
        },
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            parts = d["candidates"][0]["content"]["parts"]
            img = next(p["inlineData"]["data"] for p in parts if "inlineData" in p)
            path = os.path.join(OUT, f"{cid}_{slug}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(img))
            print(f"OK {cid} [{media}] -> {path}")
            return True
        except Exception as e:
            print(f"retry {cid} ({attempt+1}/3): {e}", file=sys.stderr)
            time.sleep(8)
    return False

def main():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set")
    os.makedirs(OUT, exist_ok=True)
    targets = sys.argv[1:] or list(CHARS)
    ok = 0
    for cid in targets:
        slug, media, desc = CHARS[cid]
        ok += gen(cid, slug, media, desc, key)
        time.sleep(2)
    print(f"done {ok}/{len(targets)}")

if __name__ == "__main__":
    main()
