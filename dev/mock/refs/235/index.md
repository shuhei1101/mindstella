# 235

コメントをスレッドにし、AI が返信・質問でき、オープン・クローズと要約を持てるようにする（[PR #235](https://github.com/shuhei1101/mindstella/pull/235)・起点 [Issue #208](https://github.com/shuhei1101/mindstella/issues/208)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「235:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を読む。
サーバーの代わりに `assets/mock.js` が記録・レビュー中のコメント・スレッドの受け口と書き換えの知らせを返し、送る・書き換える操作も画面の中で通る。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列の「見本」で状態を、「操作」で AI の返信・AI が立てたスレッドの届き方を切り替える。

| 画面 | 中身 |
| --- | --- |
| [comments](../../pages/comments/235/index.md) | コメントの一覧のレビュー中とスレッドのタブ・スレッドの一覧 |
| [comment-thread](../../pages/comment-thread/235/index.md) | スレッド 1 件（書き込み・返信・クローズ） |

| 部品 | 中身 |
| --- | --- |
| [comment-tabs](../../components/comment-tabs/index.html) | コメントの一覧のタブ |
| [thread-row](../../components/thread-row/index.html) | スレッドの行と一覧の絞り込みの帯 |
| [thread-view](../../components/thread-view/index.html) | スレッド 1 件の見出しと書き込み |
| [reply-form](../../components/reply-form/index.html) | 返信の入力 |
