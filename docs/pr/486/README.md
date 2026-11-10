# YAML として解析できない設計書（body-links.ts・Markdownの本文.ts / .tsx）の値を引用符で囲み、設計書の検査に合格させる

## 概要

develop で YAML として解析できない 3 つの設計書の値を引用符で囲み、設計書の検査（`ai_monitor.design_docs validate`）に合格させる。

## 背景

[Issue #471](https://github.com/shuhei1101/mindstella/issues/471) の要望。作業 PR [#469](https://github.com/shuhei1101/mindstella/pull/469) の実装の工程で、設計書の検査が「YAML として読めません」を返却した。
原因は今の Sprint の [#421](https://github.com/shuhei1101/mindstella/issues/421)（作業 PR [#467](https://github.com/shuhei1101/mindstella/pull/467)、commit [95b43bf2](https://github.com/shuhei1101/mindstella/commit/95b43bf2)）で、引用符の無い値に `コード: json`・`「コード: {言語}」` を記載したこと。master では解析できる。
Issue に挙がった 4 つのうち `基盤.ts.yaml` は [#476](https://github.com/shuhei1101/mindstella/pull/476)（commit [fcdb3052](https://github.com/shuhei1101/mindstella/commit/fcdb3052)）で修正済み。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [プレビュー](./プレビュー.md) | 3 つの設計書の値の記法の修正の計画書 |
