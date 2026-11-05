# 422

詳細の全画面と左のパネルを開いたとき、ほかの部分をグレーアウトし、押したら閉じる（[PR #422](https://github.com/shuhei1101/mindstella/pull/422)）。
画面は、develop のプレビューのスクリプトをつないだものに、この PR の幕・外側の押下で閉じる・ピン止め・開き直したときの戻り方を当てたもの（`assets/app.js`、当てた箇所に「422:」のコメント）と、#127 の見本の記録（`../127/assets/data.js`）を読む。
サーバーの代わり（`assets/mock.js`）は #258 と同じスレッド・レビュー中の書き込みに、保存待ちの編集 1 件を加えたもの。
スタイルは今のプレビューの `style.css` の上に、この PR の分とモック専用の操作列（`assets/style.css`）を重ねる。
各画面のモック専用の操作列の「見本」で、パネルを開いた状態を選ぶ。

| 画面 | 中身 |
| --- | --- |
| [comments](../../pages/comments/422/index.md) | コメントの一覧の幕・外側の押下で閉じる・ピン止めのボタンの 2 案・パネルの中から開いた詳細パネル・閉じて開き直したときの画面とスクロールの位置 |
| [detail-full](../../pages/detail-full/422/index.md) | 詳細の全画面の後ろの幕の濃さ |
| [decisions](../../pages/decisions/422/index.md) | 絞り込みのドロワーの幕（開く前から開いていた詳細パネルも覆う） |
| [settings-panel](../../pages/settings-panel/422/index.md) | 表示の設定のパネルの幕 |
| [pending-edits](../../pages/pending-edits/422/index.md) | 保存待ちのパネルの幕 |
