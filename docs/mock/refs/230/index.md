# 230

詳細の本文を送っても、見出しに ID とタイトルを出して何の項目か分かるようにする（[PR #230](https://github.com/shuhei1101/mindstella/pull/230)・起点 [Issue #199](https://github.com/shuhei1101/mindstella/issues/199)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「230:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を読む。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列の「案」で見出しの帯にタイトルを出す時機を、「見本」で本文の頭・本文を送った・短いタイトル・送れない項目の状態を切り替える。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/230/index.md) | 詳細パネルの見出しの帯のタイトル |
| [detail-full](../../pages/detail-full/230/index.md) | 詳細の全画面の見出しの帯のタイトル |
