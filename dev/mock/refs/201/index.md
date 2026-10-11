# 201

画面から送ったコメントを、起動スクリプトが立てた tmux のセッションの Claude Code へすぐに入力する（[PR #201](https://github.com/shuhei1101/mindstella/pull/201)・起点 [Issue #117](https://github.com/shuhei1101/mindstella/issues/117)）。
画面は 78 の左のパネルの案に、まとめて送った結果を Claude Code へ入力したかで出し分ける変更を当てたもの（`assets/app.js`、当てた箇所に「201:」のコメント）を読み、スタイルは 65・71・78 の上に出し分けの分（`assets/style.css`）を重ねる。
モック専用の操作列の「通常」で Claude Code へ入力できたとき、「Claude Code へ入力できない」で送信だけを残したときの結果を出す。
URL のハッシュに `drawer=1` を足すと、コメントの一覧を開いた状態で始める。

| 画面 | 中身 |
| --- | --- |
| [comments](../../pages/comments/201/index.md) | コメントの一覧の送った結果。文言を 3 案（1 文・2 行・入力を主に） |
