# 390

関連（related）に関係の種類といつ読むかを持たせる（[PR #390](https://github.com/shuhei1101/mindstella/pull/390)）。
画面は、develop のプレビューのスクリプトをつないだものに、この PR の関連の種類といつ読むかの表示と編集の関連の入力を当てたもの（`assets/app.js`、当てた箇所に「390:」のコメント）と、#237 の見本の記録の関連を `{to, type, when}` の並びにしたもの（`../237/assets/data.js`・`assets/data.js`）を読む。
サーバーの代わり（`assets/mock-server.js`）が記録と保存待ちの編集の読み書きに応える。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
いつ読むかを行の下に出す案 A（`a-inline-when`）と、ツールチップで出す案 B（`b-tooltip-when`）を、各画面のモック専用の操作列のタブで切り替える。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/390/index.md) | 詳細パネルの関連・参照元の種類といつ読むかと、編集の表示の関連の入力 |
| [detail-full](../../pages/detail-full/390/index.md) | 詳細の全画面の関連・参照元の種類といつ読むかと、編集の表示の関連の入力 |
| [related-list](../../components/related-list/index.html) | 関連の一覧と編集の関連の入力の状態ごとの見本 |
