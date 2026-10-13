# 235

コメントをスレッドにし、AI が返信・質問でき、オープン・クローズと要約を持てるようにする（[PR #235](https://github.com/shuhei1101/mindstella/pull/235)・起点 [Issue #208](https://github.com/shuhei1101/mindstella/issues/208)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「235:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を読む。
サーバーの代わりに `assets/mock.js` が記録・レビュー中の書き込み・スレッドの受け口と書き換えの知らせを返し、溜める・送る・クローズにする操作も画面の中で通る。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列の「見本」で状態を、「操作」で AI の返信・AI が立てたスレッド・AI のクローズ・AI のオープンへの戻しの届き方を切り替える。

| 画面 | 中身 |
| --- | --- |
| [comments](../../pages/comments/235/index.md) | スレッドの一覧 |
| [comment-thread](../../pages/comment-thread/235/index.md) | スレッド 1 件 |
| [comment-review](../../pages/comment-review/235/index.md) | レビュー中を確かめる画面 |

| 部品 | 中身 |
| --- | --- |
| [comment-head](../../components/comment-head/index.html) | コメントの一覧の見出しの帯 |
| [thread-row](../../components/thread-row/index.html) | スレッドの行と一覧の全体 |
| [thread-view](../../components/thread-view/index.html) | スレッド 1 件の見出し・書き込み・状態の記録・理由の入力 |
| [reply-form](../../components/reply-form/index.html) | 返信の入力 |
| [review-row](../../components/review-row/index.html) | レビュー中の書き込みの行 |
