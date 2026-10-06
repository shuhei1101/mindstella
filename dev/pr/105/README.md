# E2E の起動スクリプトのテストが数える MCP のツールの数を、サーバーが登録する数に合わせる

## 概要

起動スクリプトの E2E テストが、MCP のサーバーが今登録しているツールの数で通るようになる。

## 背景

[#104](https://github.com/shuhei1101/mindstella/issues/104) の不具合。
[test_launch_script.py](https://github.com/shuhei1101/mindstella/blob/develop/tests/e2e/%E5%8D%98%E4%B8%80%E3%83%A6%E3%83%BC%E3%82%B9%E3%82%B1%E3%83%BC%E3%82%B9/test_launch_script.py) の `TOOL_COUNT` が 19 のままで、[server.py](https://github.com/shuhei1101/mindstella/blob/develop/plugins/mindstella/skills/mindmap/scripts/server.py) が登録する 25 のツールと合わず `test_normal` が落ちる。
[#102](https://github.com/shuhei1101/mindstella/pull/102) のレビューで見つかり、結合テストの [test_launch.py](https://github.com/shuhei1101/mindstella/blob/develop/tests/integration/server/test_launch.py) の同じ食い違いは #102 で 25 に直した。
v0.6.0 の release の E2E（[#82](https://github.com/shuhei1101/mindstella/issues/82)）の対象に入るため、その前に直す。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [サーバー](./サーバー.md) | 起動スクリプトの E2E テストの計画書 |

## タスク一覧

- [x] ~~初期構築~~（既存リポジトリのため対象外）
- [x] ~~リバースエンジニアリング~~（現状設計書が揃っている）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] ~~PoC 検証~~（未検証の技術機構に依存しない）
- [x] ~~複合ユースケース設計~~（影響なし: テストの定数の直しだけ）
- [x] ~~デザインスタイル選定~~（画面を変えない）
- [x] ~~画面一覧・画面遷移~~（画面を変えない）
- [x] ~~単一ユースケース設計~~（影響なし: シナリオはツールの数を持たず、期待値「ツールの一覧が返る」は変わらない）
- [x] ~~モック作成~~（画面を変えない）
- [x] ~~インターフェース定義設計~~（影響なし: インターフェースを変えない）
- [x] ~~部品設計~~（画面を変えない）
- [x] ~~画面設計~~（画面を変えない）
- [x] ~~モジュール構成設計~~（影響なし: 実装を変えない）
- [x] ~~ドキュメント修正~~（更新するドキュメントが無い）
- [x] ~~単体テスト作成~~（単体テストは変えない）
- [x] ~~実装~~（実装は変えない）
- [x] ~~結合テスト作成~~（結合テストは #102 で直してあり変えない）
- [ ] E2E テスト作成
