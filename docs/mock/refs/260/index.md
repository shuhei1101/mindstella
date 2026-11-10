# 260

スレッドの書き込みでも、書き換えのまとまりの差分を指すポートによらないリンクを使えるようにする（[PR #260](https://github.com/shuhei1101/mindstella/pull/260)・起点 [Issue #257](https://github.com/shuhei1101/mindstella/issues/257)）。
画面は、develop のプレビューのスクリプトを `builder.py` の順につないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「260:」のコメント）と、#237 の見本の記録（`../237/assets/data.js`。書き換えのまとまり V-1〜V-6）を読む。
サーバーの代わりに `assets/mock.js` が記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを返す。
見本の書き込みは V-2・V-5・V-6（記録にあるまとまり）のリンクと、V-99（記録に無いまとまり）・`since`・`diff` を持たない `#` のリンク（書いた文字のまま）を持つ。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列の「案」でまとまりのリンクの見た目（A 本文のリンク・B 項目の ID のボタン）を、「見本」でスレッドとライト / ダークを切り替える。

| 画面 | 中身 |
| --- | --- |
| [comment-thread](../../pages/comment-thread/260/index.md) | スレッド 1 件の書き込み（AI・利用者・レビュー中）の中のまとまりのリンク |
| [comment-review](../../pages/comment-review/260/index.md) | レビュー中を確かめる画面の行の本文の中のまとまりのリンク |

| 部品 | 中身 |
| --- | --- |
| [thread-diff-link](../../components/thread-diff-link/index.html) | 書き込みのまとまりのリンク（案 A と案 B を並べる） |
