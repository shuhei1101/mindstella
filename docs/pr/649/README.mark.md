# 画面の状態の保持・タグの絞り込みの AND / OR・絞り込みのプリセット・記録の取得の速さをまとめて対応する

## 概要

利用者が、画面を移って戻っても離れたときの一覧・詳細パネルの位置と絞り込みから参照を再開でき、タグを押して AND / OR で絞り込め、AI が作った絞り込みのプリセットを使用でき、Windows 側のドライブのワークスペースでも画面を短い時間で開けるようになる。

## 背景

[Issue #648](https://github.com/shuhei1101/mindstella/issues/648) の束。現在の Sprint の未着手の 4 件を 1 つの作業 PR で対応する。

| Issue | 背景 |
| --- | --- |
| [#452](https://github.com/shuhei1101/mindstella/issues/452) | React の画面のルーターに `scrollRestoration` が無く、画面の切り替え・戻る・進むで一覧と詳細パネルのスクロール位置が失われる。画面の一時的な状態の保持先を、knowledge の決まり（[shuhei1101/knowledge#199](https://github.com/shuhei1101/knowledge/issues/199) で作成済み）に合わせる |
| [#187](https://github.com/shuhei1101/mindstella/issues/187) | カード・表などのタグを押しても詳細が開くだけで、そのタグで絞り込めない。部品設計『絞り込み』はタグを複数選んだときの AND / OR を定めていない |
| [#360](https://github.com/shuhei1101/mindstella/issues/360) | 特定の内容を見たいときに毎回タグで絞り込む手間がかかる。AI が利用者の見やすい単位でタグの式のプリセットを作れるようにする（画面に並べるのは [#361](https://github.com/shuhei1101/mindstella/issues/361)、画面からの保存は [#362](https://github.com/shuhei1101/mindstella/issues/362)） |
| [#547](https://github.com/shuhei1101/mindstella/issues/547) | 記録の取得（`GET /api/records`）が要求のたびにワークスペースの全ファイルを読み込み・検査し、`/mnt/c` のワークスペース（本文 805 件）で応答まで 8〜24 秒かかる。応答は 7.54 MB で圧縮もキャッシュも無い |

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.mark.md) | 子 Issue ごとの要望と終了の条件、未確定の論点 |
| [プレビュー](./プレビュー.mark.md) | 画面の状態の保持（#452）とタグの絞り込みの AND / OR・タグを押して絞り込む（#187）の計画書 |
| [サーバー](./サーバー.mark.md) | 絞り込みのプリセット（#360）と記録の取得の速さ（#547）の計画書 |
