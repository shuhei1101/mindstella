# mdmark の上で、資料に HTML と操作できる部品を埋め込み、資料を書き出せるようにする

## 概要

利用者が、Markdown の資料に埋め込んだ HTML・図・チャート・操作できる部品をプレビューでそのまま見て動かし、資料を Markdown か 1 枚の HTML で書き出せるようになる。

## 背景

[Issue #212](https://github.com/shuhei1101/mindstella/issues/212) の要望。
モックを HTML で作ると Mermaid より分かりやすく、Markdown を読みながら HTML の図も見たい。値を動かして確かめ、その値を AI へ返したい。
2026-10-15 に「mdmark の完成を待ち、mdmark に追従する」形へ書き直され、[#339](https://github.com/shuhei1101/mindstella/issues/339)（[PR #342](https://github.com/shuhei1101/mindstella/pull/342)）でプレビューの描画が mdmark v0.7.0 に置き換わった。
#342 で mindstella 側に残した用語・エイリアスの一致を mdmark へ移す範囲と、[#334](https://github.com/shuhei1101/mindstella/issues/334) から統合した正規化の受入の観点も持つ。
[#347](https://github.com/shuhei1101/mindstella/issues/347)（本文の差分・コメント・印刷を mdmark へ寄せる）はこの PR の後に進む。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
| [サーバー](./サーバー.md) | サーバー（資料の書き出し）の計画書 |
| [スキル](./スキル.md) | スキル（AI が読む HTML の作り方の資料）の計画書 |

## タスク一覧

- [x] ~~初期構築~~（既存リポジトリのため対象外）
- [x] ~~リバースエンジニアリング~~（現状設計書が揃っている）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] PoC 検証
- [x] ~~複合ユースケース設計~~（影響なし: 記録を読み返す流れは変えない）
- [x] ~~デザインスタイル選定~~（デザイン方針があり、見た目は mdmark の共通スタイルに合わせる）
- [x] 画面一覧・画面遷移
- [x] 単一ユースケース設計
- [x] モック作成
- [x] インターフェース定義設計
- [x] 部品設計
- [x] 画面設計
- [x] モジュール構成設計
- [x] ドキュメント修正（使い方/プレビューを見る.md・リファレンス/コマンド.md・リファレンス/動作環境.md・preview/licenses/README.md・skills/session/steps/取り込み.md・skills/mindmap/references/HTMLの書き方.md）
- [x] 単体テスト作成
- [x] 実装
- [x] 結合テスト作成
- [ ] E2E テスト作成
