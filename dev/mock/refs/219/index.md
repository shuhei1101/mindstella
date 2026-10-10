# 219

資料・調査にエイリアスと説明を持たせ、本文の一致した語に用語と同じツールチップで出す（[PR #219](https://github.com/shuhei1101/mindstella/pull/219)・起点 [Issue #196](https://github.com/shuhei1101/mindstella/issues/196)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「219:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を単一 UC『項目の詳細を読む』の『正常シナリオ（本文の語に一致した資料・調査へ移る）』の記録に書き換えたもの（`assets/data.js`）を読む。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
モック専用の操作列の「見本」で、ツールチップを出した・絞り込んだ・上に収まらない・資料・調査の詳細などの状態を開ける。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/219/index.md) | 詳細パネルの本文の印のツールチップと、資料・調査の説明とエイリアス |
| [detail-full](../../pages/detail-full/219/index.md) | 詳細の全画面での同じツールチップと詳細 |
| [term-tip](../../components/term-tip/index.html) | 本文の印のツールチップの状態ごとの見本 |
