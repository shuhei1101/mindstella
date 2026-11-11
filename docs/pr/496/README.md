# プレビューの結合テストの 4 件を毎回 pass させる

## 概要

プレビューの結合テストのうち、develop でも fail するか実行のたびに結果が変わる 4 件を、毎回 pass させる。

## 背景

[Issue #493](https://github.com/shuhei1101/mindstella/issues/493) の報告。
[PR #492](https://github.com/shuhei1101/mindstella/pull/492) の回帰の確認で `tests/integration/preview` を全件実行したところ 4 件が fail した。
PR #492 の変更を含まない develop でも `test_body_scroll_restored` は毎回 fail し、ほかの 3 件は実行のたびに結果が変わる。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [プレビュー](./プレビュー.md) | 詳細パネルとスレッドの画面と結合テストの計画書 |
