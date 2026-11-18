# v0.13.0 の移し替えの手順 mdmark_documents が呼ぶ mdmark を、develop ではなくタグに固定する

## 概要

v0.12.1 以前のワークスペースを開いたとき、v0.13.0 の移し替えの手順 5（`mdmark_documents`）が失敗せずに資料を mdmark の書き方へ移せるようにする。

## 背景

[Issue #578](https://github.com/shuhei1101/mindstella/issues/578) の不具合。
[PR #550](https://github.com/shuhei1101/mindstella/pull/550) で入った `mdmark_documents` は、設定に `mdmark.version` が無いとき（既定の `latest`）、mdmark の develop を `npx -y github:shuhei1101/mdmark#develop upgrade` で呼ぶ。
今の mdmark の develop（`v0.14.0+develop.d79beb4`）は出していないバージョンの移行の手順を持つため、タグを指定しない `upgrade` を断る。
このため移し替えが手順 5 で止まってワークスペースを開けず、結合テスト `test_migrate.py::test_normal_when_mdmark_documents` が fail する。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理・変更箇所の由来 |
| [サーバー](./サーバー.md) | 移し替えの手順が呼ぶ mdmark の ref の変更方針・テスト結果 |
