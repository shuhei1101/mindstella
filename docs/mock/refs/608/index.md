# 608

「レビューに追加」の後に入力欄へフォーカスを戻すかを設定で選べるようにし、スマホでは戻さないことを既定にする（[PR #608](https://github.com/shuhei1101/mindstella/pull/608)・起点 [Issue #534](https://github.com/shuhei1101/mindstella/issues/534)）。
スタイルは今のプレビューの `style.css` と [95](../95/index.md) の分の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [settings-panel](../../components/settings-panel/index.html) | 表示の設定の「レビューに追加した後のフォーカス」（自動の既定・戻さないにした・文言の案 B・置き場所の案 B・狭い幅） |
| [send-form](../../components/send-form/index.html) | コメントの入力の溜めた後のフォーカス（入力欄へ戻す・戻さないの案 A（「レビューに追加」）と案 B（結果の行）・狭い幅） |
