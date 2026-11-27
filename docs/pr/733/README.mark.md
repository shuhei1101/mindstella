# 変更履歴に「今回の差分」を追加し、変更があった項目の絞り込み・セッションの状態・埋め込みの警告・通知の公開 URL を画面とサーバーに追加する

## 概要

利用者が、最後にコメント・返信を送信した後に AI が書き換えた内容を、変更履歴の「今回の差分」で 1 回で確認できるようになる。
利用者が、全ての画面の絞り込みで変更があった項目だけを表示し、MindStella のセッションの状態と、資料に埋め込んだファイルを読み込めないことを画面で確認できるようになる。
利用者が、作業の完了の通知・停止の通知の URL を、外へ公開した URL にできるようになる。

## 背景

束の親 [Issue #732](https://github.com/shuhei1101/mindstella/issues/732) の子 6 件をまとめて対応する。

<!-- table: {"kind": "data"} -->

| Issue | 背景 |
| --- | --- |
| [#693](https://github.com/shuhei1101/mindstella/issues/693) | AI は 1 回の依頼の中で複数回 commit し、外部の変更のまとまりも挟まるので、利用者の 1 回の依頼の分を 1 回で確認できない。「前回開いてから」は [PR #723](https://github.com/shuhei1101/mindstella/pull/723)（#156）で削除済みで、依頼の単位の時点はまだ無い |
| [#158](https://github.com/shuhei1101/mindstella/issues/158) | どの項目が更新されたかを一覧で追いにくい。未読の変更のマーカーは PR #723 で入ったが、各画面の絞り込みに変更で絞る条件は無い |
| [#566](https://github.com/shuhei1101/mindstella/issues/566) | 記録の種類ごとの使い方のガイド。#518 から分けた。話し合いでは、その後にガイドの資料の作成（T-67）を中止にしている |
| [#586](https://github.com/shuhei1101/mindstella/issues/586) | [PR #582](https://github.com/shuhei1101/mindstella/pull/582) で MindStella のセッションの起動し直しの状態と失敗の理由を API の応答で返却するようにしたが、画面は表示していない |
| [#592](https://github.com/shuhei1101/mindstella/issues/592) | [PR #587](https://github.com/shuhei1101/mindstella/pull/587) で資料にファイルを埋め込めるようにしたが、読み込めないときの警告は点検の `missing_file` だけで、画面に出ない |
| [#617](https://github.com/shuhei1101/mindstella/issues/617) | 通知の末尾の URL がローカルの URL（`127.0.0.1`）で、通知を受け取ったスマートフォンなどから開けない |

<!-- /table -->

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 要望の整理 |
| [プレビュー](./プレビュー.mark.md) | 変更履歴・絞り込み・セッションの状態・埋め込みの警告の画面の計画書 |
| [サーバー](./サーバー.mark.md) | 今回の差分の始まりの記録と、通知と画面の URL の計画書 |
| [プラグイン](./プラグイン.mark.md) | 記録の種類ごとのガイドの同梱と配信の計画書 |
