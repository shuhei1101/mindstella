# 567

音声入力中の表示とつながらない表示が並んでも、トップバーを画面の幅に収める（[PR #567](https://github.com/shuhei1101/mindstella/pull/567)・起点 [Issue #560](https://github.com/shuhei1101/mindstella/issues/560)）。
スタイルは今のプレビューの `style.css` の上に、この PR の分（`assets/style.css`）を重ねる。

| 部品 | 中身 |
| --- | --- |
| [topbar](../../components/topbar/index.html) | トップバーの音声入力中とつながらない表示（今の作り・つながらない表示を短い文言にする案 A・ボタンの文字を隠す案 B・文字起こし中・ダーク。幅 1441・901・390px） |
