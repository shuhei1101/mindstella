# 123

「つながり」の画面を「ネットワーク」に改め、星の見た目の選択とノードのロックを足す（[PR #123](https://github.com/shuhei1101/mindstella/pull/123)・起点 [Issue #28](https://github.com/shuhei1101/mindstella/issues/28)）。
画面は、今のプレビューのスクリプトをつないだものにこの PR の変更を当てたもの（`assets/app.js`、当てた箇所に「123:」のコメント）と、ネットワークの 5 つの見た目の描き方（`assets/stella.js`）、126 の見本の記録を読む。
スタイルは今のプレビューの `style.css` の上に、この PR の部品とモック専用の操作列の分（`assets/style.css`）を重ねる。
見本の記録は埋め込んで読むため、コメントのボタンは出ない。コメントの印の件数は、モックの操作（`assets/mock.js`）が見本として渡す。
モック専用の操作列で、ロック（開いた鍵・閉じた鍵・ほかの項目を開いた状態・鍵の震え）、鍵を置く項目のコメントの有無、鍵とコメントの印の順（A 名前・鍵・コメントの印 / B 名前・コメントの印・鍵）を切り替える。
URL のハッシュに `look={見た目}` と `theme={light / dark}` を足すと、その見た目とライト / ダークで開く。
表示の設定の部品のモックは、見た目の選びを外した組み方（`assets/settings.js`）を読む。

| 画面 | 中身 |
| --- | --- |
| [graph](../../pages/graph/123/index.md) | ネットワーク。5 つの見た目・見た目の選び・状態の印・ロックと鍵・コメントの印と鍵の順・星座の形のタブのアイコン |
| [decisions](../../pages/decisions/123/index.md) | 検討事項のマップの節のロックと鍵（コメントの印と重ならない） |
| [settings-panel](../../pages/settings-panel/123/index.md) | 見た目の選びを外した表示の設定のパネル |

| 部品 | 中身 |
| --- | --- |
| [look-pick](../../components/look-pick/index.html) | ネットワークの見た目の選び |
| [network-label](../../components/network-label/index.html) | ネットワークの名前・状態の印・鍵・コメントの印（A・B の並び） |
| [map-lock](../../components/map-lock/index.html) | 検討事項のマップの節の鍵（コメントの印との並び） |
| [topbar](../../components/topbar/index.html) | タブの帯の「ネットワーク」と星座の形のアイコン |
| [settings-panel](../../components/settings-panel/index.html) | 見た目の選びを外した表示の設定のパネル |
