#!/bin/bash
# 肖像PNG (assets/portraits/src) → web配信用JPEG (assets/portraits/web, 長辺1024 q-high)
# macOS sips のみ使用 (依存なし)。usage: bash tools/make_web.sh
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/portraits/web
n=0
for f in assets/portraits/src/char_*.png; do
  cid=$(basename "$f" .png)
  sips -Z 1024 -s format jpeg -s formatOptions high "$f" --out "assets/portraits/web/${cid}.jpg" >/dev/null
  n=$((n+1))
done
echo "web derivatives: $n files"
du -sh assets/portraits/web
