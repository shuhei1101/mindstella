# 95

設定をワークスペースの既定（config.yaml）と個人の上書き（localStorage）の 2 段にする（[PR #95](https://github.com/shuhei1101/mindstella/pull/95)）。
画面は 52 の見本のデータと、78 のスクリプトに表示の設定のパネルとワークスペースの既定の保存を足したもの（`assets/app.js`）を読み、パネルと確かめの中身の組み方（`assets/settings.js`）は部品のモックと共有する。
スタイルは 65・71・78 の上に表示の設定の分（`assets/style.css`）を重ねる。
ワークスペースの既定（`config.yaml`）と端末の上書きは、サーバーの代わりに端末の保存領域にモックの状態ごとに置き、開き直しても戻る。
モック専用の操作列で、状態（端末で変えている・種類を絞っている・保存に失敗する・サーバーにつながらない・端末に保存できない・既定が届く・配る書き出し）と、ライト / ダークの置き場所の案（A トップバーだけ・B パネルにも）を切り替える。
状態を切り替えると、その状態の見本から始め直す。

| 画面 | 中身 |
| --- | --- |
| [settings-panel](../../pages/settings-panel/95/index.md) | 表示の設定のパネル。ワークスペースの既定にする操作の見せ方を 2 案（ボタン・区画を分ける） |
| [settings-save-confirm](../../pages/settings-save-confirm/95/standard/index.html) | ワークスペースの既定として保存する前の確かめ |
| [overview](../../pages/overview/95/index.md) | 表示しない種類に当たる概要のタイルの扱いを 2 案（タイルを残す・タイルごと外す） |

| 部品 | 中身 |
| --- | --- |
| [settings-panel](../../components/settings-panel/index.html) | 表示の設定のパネルと確かめの状態ごとの見本 |
| [topbar](../../components/topbar/index.html) | トップバーに表示の設定のボタンと、表示しない種類を外したタブの帯を足した |
