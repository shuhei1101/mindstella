# 348

mdmark の上で、資料に HTML と操作できる部品を埋め込み、資料を書き出せるようにする（[PR #348](https://github.com/shuhei1101/mindstella/pull/348)）。
画面は、develop のプレビューのスクリプトをつないだものに、この PR のエクスポートの入口とメニュー・範囲の差分を当てたもの（`assets/app.js`、当てた箇所に「348:」のコメント）と、#237 の見本の記録に資料 A-20 と書き換えのまとまり V-7 を追加したもの（`../237/assets/data.js`・`assets/data.js`）を読む。
mdmark は、HTML の埋め込みと部品を持つ commit a8c3d80（PoC の PR #349 で測ったもの）を読む。
サーバーの代わり（`../214/assets/mock-server.js`）が記録とレビュー中のコメントの読み書きに応える。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/348/index.md) | 埋め込んだ HTML・チャート・操作できる部品の描画、見出しのエクスポートの入口、範囲の差分の切り替え |
| [detail-full](../../pages/detail-full/348/index.md) | 詳細の全画面での埋め込んだ HTML の描画とエクスポートの入口 |
| [doc-export-menu](../../pages/doc-export-menu/348/index.md) | 形式を選ぶメニューと、Markdown の警告の置き方の案 A・案 B |
