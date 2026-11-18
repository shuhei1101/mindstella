# 結合テスト test_stop_session.py の準備を、無くなった MCP のツール add から記録の直接の書き込みへ修正する

## 概要

結合テスト `tests/integration/server/test_stop_session.py` の `test_normal_when_session_crashed`・`test_normal_when_forced` を、develop で pass させる。

## 背景

[Issue #574](https://github.com/shuhei1101/mindstella/issues/574) の不具合。[PR #571](https://github.com/shuhei1101/mindstella/pull/571) の結合テストの実行で見つかった。2 件は準備の `_add_pending` で MCP のツール `add` を呼ぶが、[PR #540](https://github.com/shuhei1101/mindstella/pull/540) で記録の書き込みを project-index へ移して `add` が無くなったため、`Unknown tool: add` で落ちる。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理・変更箇所の由来 |
| [サーバー](./サーバー.md) | 原因と、テストの準備の修正方針・テスト結果 |
