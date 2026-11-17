# 557

入力欄にカーソルがある間と音声入力中は記録の更新を画面に反映せず、入力・変換・録音が途切れないようにする（[PR #557](https://github.com/shuhei1101/mindstella/pull/557)・起点 [Issue #514](https://github.com/shuhei1101/mindstella/issues/514)）。
スタイルは今のプレビューの `style.css` と [529](../529/index.md) の分の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [topbar](../../components/topbar/index.html) | トップバーの「更新があります」（広い幅だけトップバーの案 A・トップバーの下の帯の案 B（推奨）・音声入力中・サーバーにつながらない・ダーク。幅 1280・390・320px） |
