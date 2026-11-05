# 一覧の画面と、詳細パネル・変更履歴と差分の表示を React へ移行する

## 概要

検討事項・タスク・資料・記録の表の一覧の画面と、詳細パネル・詳細の全画面・図の拡大・変更履歴と差分の表示を React へ移行する。

## 背景

[#443](https://github.com/shuhei1101/mindstella/issues/443) の要望で、親 [#365](https://github.com/shuhei1101/mindstella/issues/365) を分割した子 2（[#367](https://github.com/shuhei1101/mindstella/issues/367)）と子 3（[#368](https://github.com/shuhei1101/mindstella/issues/368)）を 1 本の作業 PR にまとめたもの。
子 1（[#366](https://github.com/shuhei1101/mindstella/issues/366)・[#429](https://github.com/shuhei1101/mindstella/pull/429)）で配置した React の土台（Vite・Tailwind・shadcn/ui・TanStack Router / Query・orval・Storybook・lint）とトップバー・概要の画面の上に、残りの画面を移行する。
移行を終えるまでは今の画面（`/mindstella.html`）を配信し続け、子 6（[#371](https://github.com/shuhei1101/mindstella/issues/371)）で切り替える。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
| [確認ログ](./確認ログ.md) | ユーザーへの確認事項の決着 |

## タスク一覧

- [x] ~~初期構築~~（既存リポジトリのため対象外）
- [x] ~~リバースエンジニアリング~~（現状の設計書が揃っている）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] ~~PoC 検証~~（ビルド・配信・生成・Storybook の機構は [#429](https://github.com/shuhei1101/mindstella/pull/429) の PoC で成立済み。新しく使用する TanStack Table は D-20 で採用を決めたライブラリで、使用方法は設計のライブラリ選定で確認する）
- [x] ~~複合ユースケース設計~~（影響なし: 利用者の操作の連鎖を変えない）
- [x] ~~デザインスタイル選定~~（[#429](https://github.com/shuhei1101/mindstella/pull/429) で選定したデザイン方針があり、見た目の方向を変えない）
- [x] ~~画面一覧・画面遷移~~（画面の追加・削除と画面遷移の変更を含まない）
- [x] ~~単一ユースケース設計~~（今の画面を配信し続け、シナリオの記述は子 6 の切り替えで合わせる）
- [x] ~~モック作成~~（デザイン方針のトークンで今の画面設計・部品設計の要素と操作を再現するため、見た目を作り手が決める余地が無い）
- [x] インターフェース定義設計
- [x] 部品設計
- [x] 画面設計
- [x] モジュール構成設計
- [x] ドキュメント修正（設計書/外部ライブラリ・設計書/テスト/テスト実行方法）
- [ ] 単体テスト作成
- [ ] 実装
- [ ] 結合テスト作成
- [x] ~~E2E テスト作成~~（E2E は子 6 の [#371](https://github.com/shuhei1101/mindstella/issues/371) で合わせる）
