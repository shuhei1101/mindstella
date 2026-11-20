# 項目の確認済みのマーカーを追加し、コメントの一覧の折り返し・結合テストの fail 2 件・移し替えの手順の適用・テストの後片付けを修正する

## 概要

利用者が、AI が書き換えた項目を確認したかどうかを項目ごとに残せるようになる。
あわせて、次の Sprint の小さい不具合 5 件（コメントの一覧の折り返し・結合テストの fail 2 件・移し替えの手順の適用・テストの後片付け）を修正する。

## 背景

[Issue #631](https://github.com/shuhei1101/mindstella/issues/631) は、次の Sprint の未着手の行を 1 件の最大（20 pt）までまとめた束の親。

<!-- table: {"kind": "data"} -->

| Issue | なぜ必要か |
| --- | --- |
| [#188](https://github.com/shuhei1101/mindstella/issues/188) | aituber のワークスペース（`tmp/261004_設計`）の話し合いで、画面から送信された要望（送信 S-148 を S-149 で変更）。変更履歴の未読（[#156](https://github.com/shuhei1101/mindstella/issues/156)）とは別に、項目に対して確認済みを持つ |
| [#619](https://github.com/shuhei1101/mindstella/issues/619) | React の画面のコメントの一覧のパネルで、表でない段落も横スクロールになると利用者が報告した |
| [#624](https://github.com/shuhei1101/mindstella/issues/624) | [#618](https://github.com/shuhei1101/mindstella/pull/618) の結合テストの実行で、`origin/develop` でも fail すると分かった |
| [#625](https://github.com/shuhei1101/mindstella/issues/625) | [#618](https://github.com/shuhei1101/mindstella/pull/618) の結合テストの実行で、`origin/develop` でも fail すると分かった |
| [#628](https://github.com/shuhei1101/mindstella/issues/628) | プラグインを上げた後に、ワークスペースの記録の読み込みが全て 422 になった（[#627](https://github.com/shuhei1101/mindstella/issues/627) から切り出し） |
| [#629](https://github.com/shuhei1101/mindstella/issues/629) | 結合テストの常駐サーバーが pytest の終了後も残り、端末の負荷を上げていた |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [サーバー](./サーバー.mark.md) | 確認済みの持ち方と付け外し・状態のフォルダ・移し替えの手順の集め方・テストの常駐サーバーの後片付けの計画書 |
| [プレビュー](./プレビュー.mark.md) | 確認済みのマーカーの表示と操作・書き込みの本文の折り返し・詳細パネルの最も狭い幅の計画書 |
