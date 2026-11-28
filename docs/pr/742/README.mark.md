# 画面の表・ボード・図・コメントを mdmark の部品のカスタム要素に置き換える

## 概要

利用者が、プレビューの表・ボード・図・コメントを、mdmark の部品のカスタム要素（`<mdmark-table>`・`<mdmark-view>`・`<mdmark-map>`・`<mdmark-comments>`）と同じ外観と操作で使用できるようになる。
利用者が、表形式のビューの上の「項目の追加」「列の表示」をツールチップ付きのアイコンだけのボタンで操作し、ピン止めのアイコンを見分けられるようになる。

## 背景

[Issue #737](https://github.com/shuhei1101/mindstella/issues/737) の要望。
プレビューの表・ボード・図・コメントは、mdmark の部品のカスタム要素を使用せずに組んでいる。
mdmark の配布物には、アプリの画面へ配置できるカスタム要素が入った（[shuhei1101/mdmark#793](https://github.com/shuhei1101/mdmark/issues/793)・[shuhei1101/mdmark#797](https://github.com/shuhei1101/mdmark/issues/797)）。
mdmark の部品を使用する決まりは knowledge の規約に入った（[shuhei1101/knowledge#598](https://github.com/shuhei1101/knowledge/issues/598)）。

計画の受付で、次の Issue を統合した。

| Issue | 背景 |
| --- | --- |
| [#670](https://github.com/shuhei1101/mindstella/issues/670) | 表形式のビューに mdmark の表の部品を使用できるかの調査と、表の上のボタンのアイコン化・横並び・ピン止めのアイコン（TH-1518・D-850） |
| [#350](https://github.com/shuhei1101/mindstella/issues/350) | 選んだ箇所へのコメントを mdmark の同じ機能へ移し、コメント・下書き・スレッドの箇所（`loc`）を mdmark の `{quote, prefix, suffix}` へ移し、既存のワークスペースを upgrade で移し替える（経緯は [#347](https://github.com/shuhei1101/mindstella/issues/347) のコメント） |

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [プレビュー](./プレビュー.mark.md) | 表・ボード・図・コメントの部品の置き換えと、表の上のボタンの計画書 |
| [サーバー](./サーバー.mark.md) | コメント・下書き・スレッドの箇所の形式の変更と、既存のワークスペースの移し替えの計画書 |
| [プラグイン](./プラグイン.mark.md) | 箇所を参照するコメントの取り込みのエージェントフローの計画書 |
