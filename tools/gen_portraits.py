#!/usr/bin/env python3
"""星座の軌跡 — キャラクター肖像図版ジェネレータ (スタイル検証)
青焼き図版/銅版画の人物スタディ。鍵は環境変数 GEMINI_API_KEY (コミットしない)。
usage: GEMINI_API_KEY=… python3 tools/gen_portraits.py [char_id …]
"""
import base64, json, os, sys, time, urllib.request

MODEL = "gemini-3-pro-image"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "portraits", "test")

STYLE = (
    "A single full-body figure study plate: antique cyanotype blueprint photogram "
    "combined with fine copper-engraving line work. Deep prussian-blue paper ground "
    "(dark indigo, like #0e2647), the figure rendered only in pale exposed white-blue "
    "linework and soft halation, like light fixed into photographic paper. Fine archival "
    "hatching, weathered print texture, faint paper grain, a subtle darker-blue plate "
    "border like an archaeological documentation plate. The face is softly indistinct "
    "and weathered, features only suggested, preserving the anonymity of a testimony. "
    "Quiet, dignified, memorial tone. No melodrama, no glamour, no anime style, no "
    "photorealism, no bright colors. Absolutely no text, no letters, no numbers, no "
    "captions, no watermark. Standing pose, slight three-quarter view, whole figure "
    "inside the frame with generous margins."
)

CHARS = {
    "char_01": ("aen",
        "A young farm conscript man of an early-medieval agrarian village (fantasy world, "
        "year 480 of its era): rough hand-woven tunic and leg wraps, a simple ill-fitting "
        "leather chest piece, carrying a farming hoe re-purposed as a weapon and a small "
        "cloth bundle. Lean build, work-worn hands. A few wheat stalks at his feet."),
    "char_02": ("solea",
        "A young desert nomad woman (fantasy world, year 495): layered desert robes and a "
        "long head cloth against sand wind, woven sash, a leather water skin and a "
        "shepherd's staff. Standing on a low dune, hem moving in wind, a quiet protective "
        "posture as if watching over children just outside the frame."),
    "char_04": ("lyan",
        "A court lady-scribe of an east-asian style imperial palace (fantasy world, year "
        "1350): layered silk court robes with wide sleeves, hair pinned up simply, holding "
        "a writing brush and a bound bundle of records. Composed, upright posture on a "
        "stone palace floor."),
    "char_06": ("karin",
        "A mother of a small forest tribe (fantasy world, year 1680): practical woven-fiber "
        "and hide clothing, soft hide shoes, a woven carrying band across the chest, "
        "holding the hand of a small four-year-old boy half hidden beside her. Standing "
        "among tall young trees, weary but steady."),
    "char_35": ("nagi",
        "An androgynous wandering ruin-surveyor in a far, quiet, fallen future (year 2163, "
        "low-tech salvage world, no machines): layered patched traveling clothes sewn from "
        "salvaged cloth, a heavy pack with a rolled blanket, a walking staff, an open field "
        "notebook in one hand. Dust-worn boots, standing amid faint ruin outlines."),
}

def gen(cid, slug, desc, key):
    body = {
        "contents": [{"parts": [{"text": STYLE + "\n\nSubject: " + desc}]}],
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
            usage = d.get("usageMetadata", {})
            print(f"OK {cid} -> {path} ({len(img)//1024}KB b64, tokens={usage.get('totalTokenCount','?')})")
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
        slug, desc = CHARS[cid]
        ok += gen(cid, slug, desc, key)
        time.sleep(2)
    print(f"done {ok}/{len(targets)}")

if __name__ == "__main__":
    main()
