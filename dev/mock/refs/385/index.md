# 385

find の返す量を view・include・count_only・format にして文字数を返し、項目のタグに主題のマーカーを持たせる（[PR #385](https://github.com/shuhei1101/mindstella/pull/385)）。
画面は、develop のプレビューのスクリプトをつないだものに、この PR のタグの主題のマーカーと編集のタグの入力の主題のトグルを当てたもの（`assets/app.js`、当てた箇所に「385:」のコメント）と、#237 の見本の記録のタグを `{name, main}` にして主題を持たせたもの（`../237/assets/data.js`・`assets/data.js`）を読む。
サーバーの代わり（`assets/mock-server.js`）が記録と保存待ちの編集の読み書きに応える。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
主題のマーカーは、二重丸の案 A（`a-ring`）と「主題」の文字の案 B（`b-label`）を、各画面のモック専用の操作列のタブで切り替える（採用は案 A）。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/385/index.md) | 詳細パネルのタグの主題のマーカーと、編集の表示のタグの入力の主題のトグル |
| [detail-full](../../pages/detail-full/385/index.md) | 詳細の全画面のタグの主題のマーカーと、編集の表示のタグの入力の主題のトグル |
| [docs](../../pages/docs/385/index.md) | 資料のカード・ボードのタグの主題のマーカー（表のタグの列は名前のまま） |
| [main-tag](../../components/main-tag/index.html) | 主題のタグの部品の状態ごとの見本 |
