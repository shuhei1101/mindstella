# 123

「つながり」の画面を「ネットワーク」に改め、星の見た目の選択とノードのロックを足す（[PR #123](https://github.com/shuhei1101/mindstella/pull/123)・起点 [Issue #28](https://github.com/shuhei1101/mindstella/issues/28)）。
画面は 89 の画面（絞り込みのドロワー）に、ネットワークの 5 つの見た目の描き方（`assets/stella.js`）と、見た目の選び・状態の印・ロックを足したスクリプト（`assets/app.js`）を読み、スタイルは 89 の上に見た目の選びと節の鍵の分（`assets/style.css`）を重ねる。
表示の設定のパネルは、見た目の選びを外し、上書きの一覧と確かめの項目名を「ネットワークの見た目」にしたスクリプト（`assets/settings.js`・`assets/settings-app.js`）を読む。
見た目はネットワークのドロップダウンだけで選び、個人の上書きは表示の設定のパネルと同じ保存領域に書く。
ロックはページを開いている間だけ保つ。
モックは画面ごとに HTML が分かれるため、タブを行き来したときはブラウザのタブの保存領域（sessionStorage）で引き継ぐ。
モック専用の操作列の「ロック」で、押さずに開いた鍵・閉じた鍵・ほかの項目を開いた状態・鍵の震えを見せる。
URL のハッシュに `look={見た目}` と `theme={light / dark}` を足すと、その見た目とライト / ダークで開く。

| 画面 | 中身 |
| --- | --- |
| [graph](../../pages/graph/123/index.md) | ネットワーク。5 つの見た目・見た目の選び・状態の印・ロックと鍵・星座の形のタブのアイコン |
| [decisions](../../pages/decisions/123/index.md) | 検討事項のマップの節のロックと鍵 |
| [settings-panel](../../pages/settings-panel/123/index.md) | 見た目の選びを外した表示の設定のパネル |
| [overview](../../pages/overview/123/index.md) | 概要（変えない）。タブの行き来でロックを保つことの確かめ用 |
| [tasks](../../pages/tasks/123/index.md) | タスク（変えない）。タブの行き来の確かめ用 |
| [docs](../../pages/docs/123/index.md) | 資料（変えない）。タブの行き来の確かめ用 |
| [records](../../pages/records/123/index.md) | 調査・用語集・メモ・会話ログ（変えない）。タブの行き来の確かめ用 |

| 部品 | 中身 |
| --- | --- |
| [look-pick](../../components/look-pick/index.html) | ネットワークの見た目の選び |
| [network-label](../../components/network-label/index.html) | ネットワークの名前・状態の印・鍵 |
| [map-lock](../../components/map-lock/index.html) | 検討事項のマップの節の鍵 |
| [topbar](../../components/topbar/index.html) | タブの帯の「ネットワーク」と星座の形のアイコン |
| [settings-panel](../../components/settings-panel/index.html) | 見た目の選びを外した表示の設定のパネル |
