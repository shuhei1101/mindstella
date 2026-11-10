# 127

検討事項に選択肢を必須にし、推奨・採用と状態の連動・詳細の並びと本文の描画を直す（[PR #127](https://github.com/shuhei1101/mindstella/pull/127)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「127:」のコメント）と、#126 の見本の記録を案の必須・推奨・採用と状態・Markdown の値の形へ直したもの（`assets/data.js`）を読む。
スタイルは develop の `style.css` の写し（`assets/base.css`）の上に、この PR の分（`assets/style.css`）を重ねる。
モック専用の操作列の「見本」で、未決定で推奨を持つ D-48・決定済みの D-10・要見直しの D-45・値にスクリプトを含むメモ N-1 を開ける。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/127/index.md) | 検討事項の並び（タイトル → 背景 → 案 → 採用した案と理由 → 本文）・推奨の印の 2 案・文字列の値の Markdown の描画 |
| [detail-full](../../pages/detail-full/127/index.md) | 詳細の全画面での同じ並びと推奨の印 |
