# 473

コメント・返信の入力の「レビューに追加」をアイコンだけのボタンにし、入力欄の右に配置する（[PR #473](https://github.com/shuhei1101/mindstella/pull/473)・起点 [Issue #399](https://github.com/shuhei1101/mindstella/issues/399)）。
スタイルは今のプレビューの `style.css` の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [send-form](../../components/send-form/index.html) | コメントの入力（空・入力中・ボタンのホバーとフォーカス・箇所を添えた・溜めている・溜めた・本文が空・溜められなかった・長文のボタンの縦の位置の 2 案・アイコンの案 B・項目を指さない・畳んだ形・狭い幅） |
| [reply-form](../../components/reply-form/index.html) | 返信の入力（空・入力中・ボタンのフォーカス・溜めている・レビューに追加した・追加できなかった・長文のボタンの縦の位置の 2 案・狭い幅） |
