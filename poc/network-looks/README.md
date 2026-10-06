# PoC: ネットワークの 5 つの見た目の描画の重さ

ネットワーク（旧つながり）の 5 つの見た目と、状態の印・ロックの鍵を 1000 件で描いたとき、非機能要件の決定値に収まるかを測る。

| ファイル | 中身 |
| --- | --- |
| `index.html` | 検証用のページ。前回の PoC（`poc/graph3d/index.html`）の描画ループに、見本の 5 つの見た目の描き方と、状態の印・鍵（見本 `app.js` の `drawMarks`・`drawLock`）を写す |
| `stella.js` | 見本の 5 つの見た目の描き方（`tmp/snapshots/issue28-network-2026-10-02/preview/stella.js` の写し） |
| `measure.py` | Playwright（Python）で Chrome につなぎ、操作ごとに記録してまとめる |
| `isolate.py` | 描き足しを外したページ（`?off=`）で回転とロックしたままの回転を測り、どの描き足しが重いかを切り分ける |
| `results/` | 計測の結果（1 行 1 条件）と、計測の前後の空きメモリ |

## 条件

見た目 5 つ × ライト / ダーク × 表示の幅 1280×800 と 1920×1080 × 画素の倍率 1 と 2 × 操作 5 つ（拡大・縮小、回転、押下、ロックしたままの拡大・縮小、ロックしたままの回転。各 5 秒）の 200 条件。

## 実行

```bash
# Windows の Chrome を計測用のプロファイルで、CDP を開いて立てる
"/mnt/c/Program Files/Google/Chrome/Application/chrome.exe" --remote-debugging-port=9333 --user-data-dir='C:\Users\shuhe\AppData\Local\Temp\poc-network-looks' --no-first-run about:blank &
# ページを HTTP で配る
python3 -m http.server 8765 --bind 127.0.0.1 &
CDP_URL=http://127.0.0.1:9333 PAGE_URL=http://127.0.0.1:8765/index.html MEM_PROFILE=poc-network-looks \
  python3 measure.py results/results-windows-chrome.jsonl
# 切り分け: 見た目:ライト / ダーク:表示の幅:倍率 と、外す描き足しの組（; 区切り。空は何も外さない）
CDP_URL=http://127.0.0.1:9333 PAGE_URL=http://127.0.0.1:8765/index.html MEM_PROFILE=poc-network-looks \
  python3 isolate.py results/isolate-windows-chrome.jsonl deep:dark:1920x1080:1 ";grad;sprites;spikes;sky;grad,sprites,spikes,sky"
```

## 作り直した描き方

`?draw=baked` で、星のにじみ・芯・光条を見た目・色・段ごとに一度だけ絵に焼いて毎コマは置くだけにし、線は両端の色のグラデーションをやめて単色で引く。
`?batch=0` で線を 1 本ずつ引く（まとめて 1 本のパスにすると、倍率 2 で GPU の塗りが極端に重くなる）。
`?off=`・`?bake=`・`?chunk=` は切り分け用。

```bash
CDP_URL=http://127.0.0.1:9333 PAGE_URL=http://127.0.0.1:8765/index.html MEM_PROFILE=poc-network-looks DRAW=baked BATCH=0 \
  python3 measure.py results/results-baked-single-windows-chrome.jsonl
```

| 結果のファイル | 中身 |
| --- | --- |
| `results/results-windows-chrome.jsonl` | 見本の描き方のままの 200 条件 |
| `results/isolate-windows-chrome.jsonl` | 見本の描き方で描き足しを外した切り分け |
| `results/results-baked-windows-chrome.jsonl` | 作り直した描き方で、線を色と濃さごとにまとめた 200 条件（倍率 2 で崩れた） |
| `results/isolate-baked-windows-chrome.jsonl` | 倍率 2 の崩れの切り分け（星の絵の大きさ・線のまとめ方） |
| `results/results-baked-single-windows-chrome.jsonl` | 作り直した描き方で、線を 1 本ずつ引いた 200 条件 |
