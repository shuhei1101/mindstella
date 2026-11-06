# スキルの文章の書き方のコピーを、knowledge の規約『文章の書き方』の確定版に合わせる

## 概要

スキルが記録に文章を記載するとき、knowledge の規約『文章の書き方』の確定版と同じ確認表と用語の選び方に従うようになる。

## 背景

[#30](https://github.com/shuhei1101/mindstella/issues/30) の要望。
[plugins/mindstella/skills/mindmap/references/文章の書き方.md](https://github.com/shuhei1101/mindstella/blob/develop/plugins/mindstella/skills/mindmap/references/%E6%96%87%E7%AB%A0%E3%81%AE%E6%9B%B8%E3%81%8D%E6%96%B9.md) は [#20](https://github.com/shuhei1101/mindstella/pull/20) で AI Monitor の規約『文章の追記』をコピーして作った。
コピー元の改名（[shuhei1101/ai-monitor#2363](https://github.com/shuhei1101/ai-monitor/issues/2363)）は [shuhei1101/knowledge#34](https://github.com/shuhei1101/knowledge/issues/34) へ移り、knowledge の規約『文章の書き方』（`convention-writing-style`、rev 7）として確定した。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [スキル](./スキル.md) | スキルの references の計画書 |

## タスク一覧

- [x] ~~初期構築~~（既存リポジトリのため対象外）
- [x] ~~リバースエンジニアリング~~（現状の設計書がある）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] ~~PoC 検証~~（未検証の技術機構に依存しない）
- [x] ~~複合ユースケース設計~~（影響なし: 話し合いの流れを変えない）
- [x] ~~デザインスタイル選定~~（画面を変えない）
- [x] ~~画面一覧・画面遷移~~（画面の追加・削除と画面遷移の変更を含まない）
- [x] ~~単一ユースケース設計~~（影響なし: シナリオの記述が変わらない）
- [x] ~~モック作成~~（画面を変えない）
- [x] ~~インターフェース定義設計~~（影響なし: 『話し合いの進行』は references のファイル名だけを持ち、名前は変わらない）
- [x] ~~部品設計~~（影響なし: 部品を変えない）
- [x] ~~画面設計~~（UI 項目と操作が変わらない）
- [x] ~~モジュール構成設計~~（影響なし: コードを変えない）
- [x] ~~ドキュメント修正~~（更新ドキュメントなし）
- [x] ~~単体テスト作成~~（コードを変えない）
- [ ] 実装
- [x] ~~結合テスト作成~~（新しいテストを作らない。既存の test_session.py を実装で実行のみ）
- [x] ~~E2E テスト作成~~（影響するユースケースが全て `なし`）
