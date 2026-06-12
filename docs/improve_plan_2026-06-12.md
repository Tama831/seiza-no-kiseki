# 星座の軌跡 — システム見直し 実装計画

対象: `/Users/goyama/seiza-no-kiseki/index.html`（静的1ファイル / インラインAzgaar SVG + canvas軌跡 + 素のJS）
ガードレール（全項で死守）: 巨大SVGへのCSS filter禁止 / 常時RAF禁止（イベント駆動・一回きり） / localStorageキー（stellar-v1, seiza-layer, seiza-entered）不変 / モバイル対応 / ビルドなし静的1ファイル / 倫理（鎮魂の品位・煽情/ゲーミフィケーション禁止、可愛げはOK）

注: 行番号は監査時点の値。実装直前に必ず grep で再確認してからEditを当てる（ファイルは編集で行ズレする）。

---

## (A) 即実装すべきもの — 安全・短時間・確実な価値

### A1. いいね(♡)の永続化【最優先・複数提案の統合】
**統合元**: いいね永続化系の重複提案4件（design/hour, code/hour, perf/hour ×2）を1件に統合。
**問題**: `doLike()`(L1384) はDOMの♡/♥トグルとカウント±1のみで `saveProg()` を呼ばず、`openEp()`(L1244) は毎回 `epd.likes`+♡固定で再描画。前後話ナビ往復でも、ページ再訪でも全消失。「読む=露光=不可逆な定着」の作品思想に対し、読者の唯一の能動的痕跡（赤い綴じ紐）だけが揮発するのは核心と矛盾。read は永続するのに liked が揮発する非対称も実害。
**手順**:
1. `prog`(stellar-v1) のキー走査箇所がゼロであることを再確認（新フィールド追加は後方互換）。
2. 各キャラ prog に `liked` 配列を追加。読み込み側で `p.liked = p.liked || []` の遅延初期化ガードを必ず入れる。
3. `doLike()` 内で `st.currentChar`/`st.currentEp` から `${id}_${ep}` を特定 → `liked` にtoggle追加/削除 → `markRead` 同様 `saveProg()`。
4. `openEp()` の描画時に既likedなら like-btn に `.liked` + ♥/赤を復元。カウントは `epd.likes + (自分が押していれば1)`（他者数の演出を維持し toggle整合を保つ）。
**成功条件**: 話Aで♡→次話→戻る で♡が残る／リロード後も♥点灯。**検証**: DevToolsで localStorage 'stellar-v1' に liked が入ること＋目視。**約15行・リスク極小。**

### A2. ツールチップの端クランプ【修正済み・記録のみ】
右端反転＋下端クランプ（M=8）が L1148-1158 に既に入っており preview検証済み。**追加作業なし**。A系の他修正後に回帰だけ目視確認する。

### A3. resize でズーム・パン位置が全リセットされる
**問題**: `window.addEventListener('resize',center)`(L1497) が `center()`(L664) で `st.zoom=fitZoom()`+パンを無条件初期化。モバイル回転・ウィンドウリサイズ・ソフトキーボード出現のたびに閲覧中クラスタが全景へ吹き飛ぶ。
**手順**: resize ハンドラを「現zoom>新fitZoomなら維持して `clamp()`+`applyT` のみ呼ぶ」最小実装に変更（clampが中央寄せ内蔵）。イベント駆動のままなのでRAFガードレール非抵触。
**成功条件**: ズーム状態でウィンドウ幅を変えても全景に戻らない。**数分〜30分。**

### A4. 物語fetch失敗時の沈黙を静かな表示に
**問題**: `loadStories()` の各fetchが `catch(e){}`(L1492) で握りつぶし、STORIES空のまま `renderDots` すると全dotが locked(pointer-events:none) で「触っても何も起きない」沈黙。発生条件: file://直開き(CORS全失敗) / Pages一時404。
**手順**: `loadStories().then()` の後(L1556付近)で `Object.keys(STORIES).length===0` を判定し `#complete-note` を流用して静かな一文を表示。`location.protocol==='file:'` 時は「サーバー経由で開いてください」の専用文言。感嘆符なし・記録調。
**成功条件**: file://で開くと無言ではなく静かな案内が出る。**10-20行。**

### A5. キーボード/スクリーンリーダで星を辿れる a11y 基盤（最小版）
**問題**: index.html全体に role/aria-*/tabindex が0件。roster削除済みで dotクリックが唯一の入口のため、キーボード/SR利用者は35人の誰一人開けず作品にアクセス不能。「鎮魂の品位」を掲げる作品の最も本質的な欠落。
**手順（最小・価値の9割）**:
1. `renderDots()` の hasStory な `<g class='char-dot'>` に `tabindex='0'` `role='button'` `aria-label=\`${c.name} ${c.era} ${p.read.length}/${c.episode_count}話\``。
2. keydown(Enter/Space)→`openChar`。focus時 `setHover()` 呼び出しでhoverと視覚パリティ（1行）。
3. CSS: `.char-dot:focus-visible .star-core{stroke:var(--cy-light);stroke-width:1.4}`。
**不採用**: `role='application'`（矢印キー完全実装しない限りSRの仮想カーソルを殺すアンチパターン）。Tab巡回のみ。
**成功条件**: Tabで星を巡れ、Enterで証言が開く。**視覚変化はfocus ringのみ。** モーダルのdialog化(A6)と相補。

### A6. リーダ/図鑑モーダルのフォーカストラップ＋復帰＋ARIA【2提案統合】
**統合元**: story-overlay/pmodal のa11y提案（design/halfday, perf/halfday）を統合。
**問題**: モーダルを開いてもフォーカスは背後地図に残り(.focus()=0件)、Tabが裏のUIボタンへ抜ける。閉じても発火元へ戻らない。pm-img alt固定「人物図版」。
**手順**:
1. `openEp`/`openPortrait` 末尾で内部の最初の操作要素(story-close / pm-close)に `.focus()`、`st._lastFocus` に発火元を保持し close時に復帰。
2. overlay/modal の keydown で Tab/Shift+Tab を先頭↔末尾でループ（定番トラップ15行）。閉時に `inert` 付与でTab順から除外（実装が簡潔化）。pmodal(z220)とstory-overlay(z100)同時表示時はトラップを最前面のみ有効に。
3. `role='dialog'` `aria-modal='true'` `aria-label`、`pm-img.alt` を `${c.name} — ${MEDIA_LABEL[p.media]}` に動的化、like-btn に `aria-pressed`（liked同期、A1と整合）。
**成功条件**: Tabがモーダル内で循環し、Escで閉じると元の星にフォーカスが戻る。**視覚変化ゼロ。**

### A7. 入口ゲートのフォーカス＋警告のSR伝達
**問題**: entry-gate(L259-) 表示時 `#eg-enter` に初期フォーカスなし、コンテンツ警告 `.eg-warn` がSRに構造的に届かない。
**手順**: ゲート表示時（再訪スキップしない位置）に `btn.focus({preventScroll:true})`、gate に `role='dialog'` `aria-modal` `aria-labelledby=eg-title` `aria-describedby=eg-warn`。Esc非対応のまま（警告を読ませる）。
**成功条件**: SRで内容警告が読み上げられ、Enterで入場。**鎮魂作品の倫理の中核。約20分。**

### A8. forced-colors / prefers-contrast の最小対応
**問題**: `prefers-contrast`/`forced-colors` が0件。意図的に淡い青写真パレットで、弱視・屋外・OSハイコントラスト下では証言星の所在すら見えない。
**手順**: `@media(prefers-contrast:more){...}` で星core opacity底上げ・UIヒント/本文の明度底上げ。背景なし要素に forced-colors の背景保険。デフォルト表示・淡さは不変（media query内に閉じる）。
**成功条件**: DevToolsのforced-colorsエミュで星とUIが見える。**CSS10-15行・30-60分。**

### A9. 衛生（dead code / stale コメント）まとめて掃除【3提案統合】
**統合元**: buildMap dead code / st.vrMode未使用 / Phase 1 stale コメントの衛生提案。
**手順**:
1. **buildMap()ブロック削除**(L1439付近〜, CARTOGRAPHY 約75行): 全呼び出しゼロを grep再確認の上で削除（git履歴に残る・可逆）。innerHTMLで現行静的地図を上書きする footgun かつ旧暗色パレット(#14161e)=Cyanotype以前の遺物。
2. **`st.vrMode` 削除**: 宣言のみで read/write ゼロ（実フラグは `st.vrView`）。混同による将来バグの芽。
3. **L610 コメント更新**: 「Phase 1 (chars 01–03 only)」→ 現状（全35話 fetch）。`loadStories()` の episode_count上書き(L1490)にWhyコメント1行。
4. **L1389-1390 の "removed per feedback" tombstone**: 削除せず1行に圧縮（機能再追加防止の履歴価値を保つ）。
**成功条件**: grep で buildMap/st.vrMode が消え、ページ挙動が不変。**挙動変更ゼロ。**

### A10. 同一座標(966,224)の交差マーカー二重生成
**問題**: CROSS_POINTS(L586) に [char_30,char_13] と [char_35,char_13] が同一 coord:[966,224]。双方読了で `renderDots` の addMark が透明hit円(r14)を同一点に二重append → z順後勝ちで char_35側tipのみhover可、「ソウラ×トウカ」の交差が最も深く読んだ人から恒久的に読めない。
**手順**: complete フィルタ後に同一coordをグループ化し、成立中の cross point の tip を `\n\n` 連結して mark を1個だけ描画（芯・内輪の重複も除去、harm判定は連結後tipで）。**±3pxオフセット案は二重露光モチーフを弱めるので不採用。** 成立集合は読書進行で変わる点に注意。
**成功条件**: 全読了時に1マーカーから両方の交差説明が読める。**20-30分。**

### A11. ズームヒントの書体を可読に（PC限定）
**問題**: `#zoom-hint`(L148) の 'scroll: zoom / drag: pan' が Major Mono Display（装飾的全小文字）で機能テキストとして判読しづらい。coarse pointerでは非表示なのでPC限定。
**手順**: `#zoom-hint` の font-family を `var(--font-en)`(Spectral) に変更＋letter-spacing微調整。整理印ラベル(#title-stamp等)の書体は温存。日本語併記は任意（後決め）。
**成功条件**: 操作説明が読みやすくなる。**CSS1プロパティ・数分。**

### A12. ep-meta の点線下線を除去（帳票感の解消）
**問題**: `.ep-meta span`(L122) の border-bottom 点線が時刻/場所/語り手を律儀に区切り事務帳票化。さらに人物名(L207)が「点線=クリック可」言語を使っており非インタラクティブな ep-meta の点線はアフォーダンス衝突。
**手順**: 点線除去、既存 `--arc-pencil` ラベルは維持（第1案）。VR variant(L183-185)の border-color も併せて削除。**「時/場/人」1行畳み（第2案）はモバイル折返しで非推奨。**
**成功条件**: メタ情報がノイズなく本文の静謐さに馴染む。**CSSのみ・数分。**

### A13. 海面微光のモバイル常時アニメ停止
**問題**: `#sea-drift` の80s transformアニメが640pxブロックに含まれず常時ループ、動くblendレイヤの毎フレーム再合成コストがpan/zoom中のジャンク要因。
**手順**: `@media(max-width:640px)` 内に `#sea-drift{animation:none}` の1行のみ。opacity .07の80sアニメは知覚されず視覚劣化僅少。**`#paper-grain` の mix-blend除去は不採用**（暗いプルシアンブルー地に乳白ヘイズが乗り感光紙質感が濁る）。
**成功条件**: モバイル幅でsea-driftアニメが止まる。**1行・倫理中立。**

### A14. 肖像の色温度統一（CSSトーン・低コスト案A）
**問題**: web/肖像の平均彩度が char_06=34.5〜char_01=80.0 と倍以上開き、図鑑/hover胸像で「同じ感光紙の版」に見えない。
**手順**: `.pm-img img` と `#pcard` にシアン統一トーンを掛ける（小さな<img>/divなのでSVG-filter禁止に非抵触・可逆）。**実装時2点必須**: (1) #pcard は既に blur現像アニメ中なので両状態(blur側・.show側)に色filterを合成して書く、(2) 提案値 `sepia(.15) hue-rotate(170deg)` は残存ブルーが暖色化する恐れ→saturate先行＋sepia強化 or `mix-blend-mode:color` オーバーレイで目視チューニング。**B案(画像バッチ再処理)は不採用。**
**成功条件**: 35枚が1つの現像液下に見える（preview目視）。**hour級。** ※色味の最終判断はたまさんの目視確認推奨。

### A15. 読了数の静かな表示（◯/35、感光メタファー）
**問題**: 35人規模なのに読了の現在地を示すUIが星の状態以外ゼロ。再訪時に「あと誰が残っているか」が掴めず Closure の手応えが弱い。
**手順**: `#sub-count`(L272) を読了数連動に。`renderDots()` 末尾（読了毎に呼ばれる）で `CHARS.filter(c=>isComplete(c.id)).length` を数え textContent更新。文言は記録調（例「35の証のうち 7 が現像された」）、**0件時は現行静的表示を維持**。**バー/%/ゲージは却下**（ゲーム文法）。
**成功条件**: 読むほど数が増え、0件で静的表示。**renderDots末尾1-3行。**

### A16. 衛生コメント（minutes級・A9に含めず単独でも可）
L1382-1383 等の削除済み機能コメント整理は A9-4 に統合済み。重複ナシ。

---

## (B) たまさんに提案して選んでもらうもの — 方向性判断が要る

### B1. モバイルの星タップ成立【halfday・実装可だが体験設計判断あり】
スマホ縦持ちで fitZoom≈0.185 → タップ目標約1.7px、証言を読む主経路が事実上死亡＝「モバイル対応必須」ガードレール違反級。
- 案: (1) `pointer:coarse` 時のみ hit半径↑(r6.5)・decluster MIN↑(16)、(2) 入場後一度だけ「星をタップして読む／二本指で拡大」のトースト（layer-hint流用・localStorage一度きり）。
- **注意**: 定数↑単独では約2.4pxにしかならず、(1)(2)同時実装で初めて成立。→ どこまでやるか（最小=定数のみ / 完全=ヒント込み）の判断を仰ぐ。**やる/保留/降ろす？**

### B2. 人物への深リンク＋共有（一人を手渡す）【2-4時間】
URL状態が一切ない（hash/share/replaceState 0件）。35人の入口がトップ1個だけでSNSで「この一人を読んで」と送り出せない。
- 採用形（要調整3点）: OGPは静的1ファイルで人物別不可なので落とす／**人物単位hash→openChar(id)** に限定（ep直リンクは「既読分のみ開示」を破る）／未解放ナギ無効化＋入場ゲート後にhash消費。
- 「拡散」でなく「一人に手渡す」設計（文言「○○の証を、誰かに手渡す」）。Closure思想に合致。**やる/保留/降ろす？**

### B3. 年代軸（時の現像）— 1683年を触れる時間軸に【day+】
era が色温度でしか可視化されておらず「時を越えた邂逅」が地図上で掴めない。画面下端に薄いシアンの年代スケール、星をera順に打ち、hoverで `setHover()` 点灯、クリックでpan&zoom（一回きりtween=RAF適合）。
- **必須条件2点**: `charVisible()` で未開放ナギ(char_35)を除外／AE1907-1975に約12人密集の目盛り衝突処理＋下端UI(#layer-btn/#zoom-hint)の配置干渉回避。
- 価値は主題直結で高いが工数大・新規UI。**やる/保留/降ろす？**

### B4. 交差点の「二人の証言を並置」読書【halfday＋編集判断】
最強の倫理的核（クラウス×サナ＝同じ村の虐殺）が白い焼き跡マークだけで読書として回収されていない。両者読了済み交差マークのクリックで二段組（左:加害側 / 右:被害側）を静かに並べる。新規本文ゼロ（既存epのwaypoint_indexを交差座標に紐付け＋ep番号フィールド付与）。
- **重さ**: story-overlay流用より重い（新CSS＋モバイル縦積み＋VR変種）、14組分の加害/被害並置の編集判断が要る。**やる/保留/降ろす？**

### B5. 交差点の発見可能性「未定着の予兆」【1時間】
CROSS_POINTS(14組)は両者読了ゲートで初見者がほぼ到達不能。片側だけ読了の交差点を「未定着の予兆」として極薄点で先出し（pointer-events:none・定着前tipなしでネタバレ防止）、もう片方を読むと二重露光が定着。潜像→定着は現像の正規語彙で感光メタファー内。renderDotsのループに片側読了分岐5-10行。**やる/保留/降ろす？**

### B6. ナギの巡礼「円環構造」相互リンク【1-2時間】
ナギ(char_35, NAGI_GATE 5人読了で出現)の5廃墟から、かつて生きた人(char_03/05/06/13/21)へジャンプする一方向リンクを pm-route下に。35人が一つの星座へ閉じる。NAGI_MARKSのnoteは追加文章ゼロで構造化可。**逆方向(char_03→ナギ)はナギ未出現時の存在バレになるので実装しない（ナギ→5人の一方向限定）。やる/保留/降ろす？**

### B7. 読了直後の「次の人へ」導線【halfday＋感性確認】
`finishNext()`(L1286) が読了時 closeStory するだけで次の未読星への手がかりゼロ。
- **正しい形（提案そのままは不可）**: story-overlayは全画面74%スクリムで読了の一回きり不可逆エフェクト(fix-ring/酸化/fireDoubleExpose/finale)を覆い隠す → 従来通りclose→定着演出を見せる→約2秒後に控えめな非モーダル導線＋対象星の静かなパルス。finale・ナギ出現時は抑止。自動連鎖せず一拍置く。
- エフェクト順序とトーンに作者の感性確認が要る。**やる/保留/降ろす？**

### B8. 再訪導線「おかえり／続きから」【halfday・B7と一部重複】
再訪時に「前回どこまで」「今何が新たに見られるか（交差出現・ナギ解放）」を伝える導線ゼロ。入場後 complete-note流用で4-5秒「紙は前回の露光を覚えている／◯/35／最後の□□の続きへ」、新交差成立は件数だけ示唆（場所は明かさない）。`lastRead` を stellar-v1 に追加（後方互換）。
- **要件**: pan-to-character関数が現存せず新設（zoom/clamp絡みでモバイルズレ注意）、既知交差集合の保存がもう1つ要る。**B7と統合 or どちらか一方を推奨。やる/保留/降ろす？**

### B9. 地図から図鑑へ直接入る入口【1-2時間】
openPortrait の入口が本文中の .pname のみ(L1262)で、地図を眺める段階で図鑑に到達できない。
- **採用形**: hover tooltip内案は #tooltip が pointer-events:none で不成立 → **副次クリック(contextmenu)＋長押し** のみ。dot clickは openChar に既バインドのため stopPropagation必須、モバイル長押しはパン閾値判定が必要（showPCardはcoarseで無効＝長押しが唯一のモバイル入口）。露光ルールは openPortrait が既読waypointのみ開示で自動保持。**やる/保留/降ろす？**

### B10. 再訪者へ entry-gate を分岐【20-30分・B8と重複】
seiza-entered時に即スキップだが、読了がある再訪者に「前に触れた星は、まだ紙に残っている」を入場後2.6秒に一度だけ（walker初回spawnと重ねる）。sessionStorageガードで毎リロード発火防止（保護localStorageキー非接触）。**B8と機能が重なるため、B8採用ならB10は不要。やる/保留/降ろす？**

### B11. フォント非ブロッキング化【任意・却下寄り】
noscript フォールバック（JS無効時の無言画面に静かな一文）は **A群相当で即実装可**。一方 `media='print' onload` のフォント非ブロッキングhackは entry-gate（最初の露光）に毎回FOUTを起こしモーション言語に逆行 → **不採用推奨**。noscript一文だけ拾うか確認。**やる/保留/降ろす？**

---

## (C) 落としたが記録に値するもの（1行ずつ）

- C1. CROSS_POINTS ±3pxオフセット案 — 二重露光モチーフを弱めるため不採用（A10は tip連結で対応）。
- C2. 露光ゲージ/プログレスバー — 常設HUD＝ゲーム文法、情報増ゼロで却下（A15は数のみ）。
- C3. role='application' を #map-root に付与 — 矢印キー完全実装しない限りSR仮想カーソルを殺すアンチパターン。
- C4. #paper-grain の mix-blend-mode 除去 — モバイルで感光紙の乳白ヘイズが濁るため不採用（A13はsea-driftのみ）。
- C5. 肖像のバッチ再トーンマップ（B案）— CSS案(A14)で十分、過剰につき不採用。
- C6. ep-meta「時/場/人」1行畳み（第2案）— モバイル折返しと明瞭さで非推奨（A12は点線除去のみ）。
- C7. .pname に ◉/▸ マーカー追加 — タップで図鑑が開く（最強の応答）ため誤診、装飾ノイズで却下（タップ領域padding拡大のみ採用→A6/B9圏で吸収）。
- C8. 人物別OGP — hash+静的1ファイルで原理的に不可（B2は deep link+share に限定）。
- C9. ep直リンク(#id-ep) — 「露光は一方向・既読分のみ開示」を破る（B2は人物単位hashに限定）。
- C10. buildMap のコメント化保存(B案) — innerHTML footgunを残すため削除(A9)に劣後。
- C11. #zoom-hint 日本語併記 — 任意・後決め（A11は書体変更のみ必須）。
- C12. media='print' onload フォント非ブロッキング — entry-gateにFOUTを起こしモーション言語逆行で却下（B11はnoscriptのみ）。
- C13. nav-btn への aria-label — 可視テキストありで不要（提案が一部過大）。
