#!/usr/bin/env python3
"""星座の軌跡 — キャラクター肖像図版ジェネレータ v3 (本番: 全35人、データ駆動)
方式B: 時代でメディア進化 — 銅版画(AE<1500) → 青焼き写真(<2000) → スキャン(2000+、ナギ系=琥珀/VR=シアン)。
全員「可愛げ・親しみやすさ」: 絵本的なやわらかい人物造形、顔を見せる(2026-06-12 たまさん決定)。
入力: /tmp/seiza_chars.json (id/era/origin/vr) + /tmp/seiza_bios.json (appearance_en)。
鍵は環境変数 GEMINI_API_KEY (コミットしない)。
usage: GEMINI_API_KEY=… python3 tools/gen_portraits.py [--force] [char_id …]
"""
import base64, json, os, sys, time, urllib.request

MODEL = "gemini-3-pro-image"
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "assets", "portraits", "src")

CHARM = (
    "The character is drawn with a gentle, approachable, contemporary storybook "
    "sensibility: soft rounded facial features, kind readable eyes, a calm warm "
    "expression, slightly stylized appealing proportions. The face is clearly visible "
    "and likable. NOT chibi, NOT glossy modern anime, no oversized sparkling eyes, "
    "no glamour. Worn clothes and tired-but-resilient warmth keep the quiet dignity "
    "of a war testimony. Single full-body figure (plus a companion only if the "
    "subject description explicitly includes one), standing, slight three-quarter "
    "view, whole figure inside the frame with generous margins. Absolutely no text, "
    "no letters, no numbers, no watermark."
)

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

def media_of(c):
    y = int(c["era"].replace("AE ", ""))
    if y < 1500: return "engraving"
    if y < 2000: return "photo"
    return "scan_cyan" if c.get("vr") else "scan_amber"

def gen(cid, media, desc, key):
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
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.load(r)
            parts = d["candidates"][0]["content"]["parts"]
            img = next(p["inlineData"]["data"] for p in parts if "inlineData" in p)
            path = os.path.join(OUT, f"{cid}.png")
            with open(path, "wb") as f:
                f.write(base64.b64decode(img))
            print(f"OK {cid} [{media}]", flush=True)
            return True
        except Exception as e:
            print(f"retry {cid} ({attempt+1}/3): {e}", file=sys.stderr, flush=True)
            time.sleep(10)
    print(f"FAIL {cid}", flush=True)
    return False

# テスト6人の確定版 (assets/portraits/test/ のスラッグ付きPNGをsrcへ採用コピーする)
APPROVED = {"char_01": "char_01_aen.png", "char_02": "char_02_solea.png",
            "char_04": "char_04_lyan.png", "char_06": "char_06_karin.png",
            "char_22": "char_22_rai.png", "char_35": "char_35_nagi.png"}

def main():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY not set")
    os.makedirs(OUT, exist_ok=True)
    chars = {c["id"]: c for c in json.load(open("/tmp/seiza_chars.json"))}
    bios = json.load(open("/tmp/seiza_bios.json"))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    targets = args or sorted(chars)
    ok = skip = 0
    for cid in targets:
        dst = os.path.join(OUT, f"{cid}.png")
        if cid in APPROVED and not force and cid not in args:
            srcp = os.path.join(ROOT, "assets", "portraits", "test", APPROVED[cid])
            if os.path.exists(srcp):
                import shutil; shutil.copyfile(srcp, dst)
                print(f"COPY {cid} (approved test plate)", flush=True); skip += 1; continue
        if os.path.exists(dst) and not force and cid not in args:
            print(f"SKIP {cid} (exists)", flush=True); skip += 1; continue
        era_line = f"This person lives in the era year {chars[cid]['era']} of a fictional world. "
        ok += gen(cid, media_of(chars[cid]), era_line + bios[cid]["appearance_en"], key)
        time.sleep(2)
    print(f"done generated={ok} reused/skipped={skip} / {len(targets)}")

if __name__ == "__main__":
    main()
