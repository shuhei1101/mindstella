# 本文の差分・印刷を mdmark の機能に置き換え、画面・文書・テストの小さい修正 14 件をまとめて対応する

## 概要

利用者が、プレビューの本文の差分と印刷を mdmark の機能で使用でき、画面の見た目と操作・公開ドキュメント・テストの小さいずれを修正した状態で使用できるようになる。

## 背景

[Issue #666](https://github.com/shuhei1101/mindstella/issues/666) の束。次の Sprint の未着手の 15 件を 1 つの作業 PR で対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#347](https://github.com/shuhei1101/mindstella/issues/347) | プレビューの描画を mdmark へ置き換えた [#342](https://github.com/shuhei1101/mindstella/pull/342) で、本文の差分と印刷は mindstella 側の実装を使用し続け、mdmark の同じ機能を止めた。React の画面も `body-view.tsx` で mindstella 側の差分を描き、`MDMARK_FEATURES` で `print` を止めている |
| [#147](https://github.com/shuhei1101/mindstella/issues/147) | 本文の項目の ID のボタンは `title` にタイトルだけを持ち、状態が分からない |
| [#478](https://github.com/shuhei1101/mindstella/issues/478) | モジュール構成『ビルド.py』の `SCRIPT_FILES` が `builder.py` と食い違うという報告。[#644](https://github.com/shuhei1101/mindstella/pull/644) で今の画面と一緒に両方から削除された |
| [#488](https://github.com/shuhei1101/mindstella/issues/488) | `docs/guide/` のページのタイトル直下の 1 行が、`docs/guide/index.yaml` の `summary` と一致しない |
| [#548](https://github.com/shuhei1101/mindstella/issues/548) | 今の画面の雛形が mermaid を `defer` で読み込み、初期化が待っていた。今の画面は #644 で削除された |
| [#634](https://github.com/shuhei1101/mindstella/issues/634) | `topbar.js` を読み込むモックでスクリプトのエラーが出るという報告。読み込む今の画面のスクリプトは #644 で削除された |
| [#636](https://github.com/shuhei1101/mindstella/issues/636) | v0.14.0 の変換のスクリプト 2 本の行が `plugins/mindstella/files.yml` に無い |
| [#638](https://github.com/shuhei1101/mindstella/issues/638)・[#664](https://github.com/shuhei1101/mindstella/issues/664) | ボードの横スクロールの領域に左右の余白が無く、カードが 0 枚のときキーボードで届かない |
| [#646](https://github.com/shuhei1101/mindstella/issues/646) | 資料の画面のカードの見出しが `h1` の次に `h3` で、見出しのレベルを飛ばしている |
| [#647](https://github.com/shuhei1101/mindstella/issues/647) | `test_diff_mark_stories.py::test_removed` の期待値が、[#640](https://github.com/shuhei1101/mindstella/pull/640) で「削除した」に変わった部品より前の「消した」のまま |
| [#655](https://github.com/shuhei1101/mindstella/issues/655) | スマホの幅では資料の詳細パネルが最初から最大で、最大化のボタンが押しても変わらない |
| [#657](https://github.com/shuhei1101/mindstella/issues/657) | コメントの一覧のロックの解除の状態を、錠のアイコンを傾けて出している |
| [#662](https://github.com/shuhei1101/mindstella/issues/662) | 概要のページはビューポートの幅（`max-md:`）で切り替え、サイドパネルを広げて狭くなっても 1 列にならない |
| [#665](https://github.com/shuhei1101/mindstella/issues/665) | 絞り込みのドロワーを開いても、画面設計・シナリオのとおりのグレーアウトと `inert` が無い |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件 |
| [プレビュー](./プレビュー.mark.md) | プレビューの画面・部品・テストの計画書 |
