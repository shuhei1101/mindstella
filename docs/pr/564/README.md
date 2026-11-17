# 結合テスト test_preview_url.py の diff を指定する 2 件を、配信を起動していない準備で pass させる

## 概要

結合テスト `tests/integration/server/test_preview_url.py` の `test_normal_when_diff_given`・`test_error_when_diff_not_found` を、develop で pass させる。

## 背景

[Issue #562](https://github.com/shuhei1101/mindstella/issues/562) の不具合。[PR #558](https://github.com/shuhei1101/mindstella/pull/558) の結合テストの実行範囲で見つかった。2 件はまとまり V-1 を持つワークスペースを準備した後の `preview_url` で `started` が真になる（配信をまだ起動していない）ことを前提にするが、develop では偽が返る。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理・変更箇所の由来 |
| [サーバー](./サーバー.md) | 原因と、テストの準備の直し方・テスト結果 |
