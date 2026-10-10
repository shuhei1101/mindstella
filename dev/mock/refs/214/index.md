# 214

資料の本文を HTML でも書けるようにする（[PR #214](https://github.com/shuhei1101/mindstella/pull/214)・起点 [Issue #151](https://github.com/shuhei1101/mindstella/issues/151)）。
画面は、develop のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「214:」のコメント）と、#179 の見本の記録に本文を HTML で持つ資料を足したもの（`assets/data.js`）を読む。
サーバーの代わり（`assets/mock-server.js`）が記録とレビュー中のコメントの読み書きに応え、プレビューをサーバーにつながった状態で開く（選んだ箇所のコメントの入口を出す）。コメントは開いている間だけ持ち、開き直すと 0 件に戻る。
HTML の本文の行の印は、サーバーが本文を配る前に足す印の代わりに `assets/app.js` が足す。
スタイルは develop の `style.css` の写し（`assets/base.css`）の上に、この PR の分（`assets/style.css`）を重ねる。
見本の記録で HTML の本文を持つのは、A-11「設定のパネルの画面の流れ（モック）」（`<style>` で `*`・`body`・`p` を塗り、見出し・段落・図・表を持つ。V-5「画面の流れのモックを直す」で 2 つ目の段落を書き換えた）と、A-12「保存のボタンの見本（スクリプトを含む HTML）」（`<script>`・`onerror` の画像・`onclick` のボタンを持ち、動けば操作列の「本文のスクリプト」が「動いた」に変わる）。
モック専用の操作列で、見本の資料と時点（差分を出さない・V-5・前回開いてから）を切り替える。

| 画面 | 中身 |
| --- | --- |
| [docs](../../pages/docs/214/index.md) | 資料のカード・ボード・表の本文の形式のバッジと形式の列。バッジの置き場所を 2 案 |
| [detail-panel](../../pages/detail-panel/214/index.md) | ヘッダーの形式のバッジ・HTML の本文の枠・枠の中で選んだ箇所のコメントの入口・スクリプトを含む本文。HTML の本文の差分の見せ方を 2 案 |
| [detail-full](../../pages/detail-full/214/index.md) | 詳細の全画面での同じ表示と差分の 2 案 |
| [search](../../pages/search/214/index.md) | 全体の検索で HTML の本文を描いた文で当てる |

| 部品 | 中身 |
| --- | --- |
| [body-format-badge](../../components/body-format-badge/index.html) | 本文の形式のバッジ（形式ごと・ほかの札と並べたとき・カードの案 A と案 B・ボード・表の列・詳細のヘッダー・ホバーとフォーカス・狭い幅） |
| [html-body-frame](../../components/html-body-frame/index.html) | HTML の本文の枠（描いた本文・<style> が漏れない・描く前・スクリプトを含む本文・差分の案 A と案 B・差分を出せない・狭い幅） |
