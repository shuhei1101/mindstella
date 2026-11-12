# 起動スクリプトの登録で文字起こしの環境変数（MINDSTELLA_TRANSCRIBER・MINDSTELLA_TRANSCRIBER_URL）を登録できるようにする

## 概要

利用者が、起動スクリプトの登録で文字起こしのサービスと接続先（`MINDSTELLA_TRANSCRIBER`・`MINDSTELLA_TRANSCRIBER_URL`）を登録し、新しいシェルで起動した常駐サーバーで使用できるようになる。

## 背景

[Issue #501](https://github.com/shuhei1101/mindstella/issues/501) の報告（[作業 PR #500](https://github.com/shuhei1101/mindstella/pull/500) のスコープ外から切り出した）。
環境変数を付けずに常駐サーバーを再起動すると、プレビューで文字起こしのサービスが起動していないと表示された（2026-11-11）。
[docs/guide/コマンド.md](https://github.com/shuhei1101/mindstella/blob/2b1d2c2cd1cb474a14209aaa308bdad2b02c881c/docs/guide/%E3%82%B3%E3%83%9E%E3%83%B3%E3%83%89.md) とインターフェース定義『起動スクリプトの登録』は、`--env` で文字起こしの 2 つのキーを受けると記載しているが、`register.py` の `ENV_KEYS` に無く、`--env` で拒否される。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [サーバー](./サーバー.md) | 登録のスクリプトが受ける環境変数のキーの計画書 |
