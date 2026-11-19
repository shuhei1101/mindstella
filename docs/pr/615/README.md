# docs/ の文書のマーカーを mdmark upgrade で JSON の記載へ移す

## 概要

`docs/` の文書のマーカーの引数を、mdmark の JSON のオブジェクトの記載へ移す。

## 背景

[#512](https://github.com/shuhei1101/mindstella/issues/512) の要望。
mdmark は [shuhei1101/mdmark#477](https://github.com/shuhei1101/mdmark/pull/477) でマーカーの引数を JSON のオブジェクトで記載できるようにし、v0.11.0 から `mdmark upgrade` で今の書き方を書き換える移行の手順を配布した。
今の書き方は [shuhei1101/mdmark#479](https://github.com/shuhei1101/mdmark/issues/479) で参照されなくなる。
2026-11-19 の develop では、`docs/` の Markdown のうち約 160 ファイルが今の書き方のマーカー（`<!-- table: data -->` など）を持つ。

起点 Issue が対象に挙げた `plugins/mindstella/skills/mindmap/references/文章の書き方.md` は [#565](https://github.com/shuhei1101/mindstella/pull/565) で削除済み。
MindStella のワークスペースの文書を移す手段は [#532](https://github.com/shuhei1101/mindstella/issues/532) が扱う。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
