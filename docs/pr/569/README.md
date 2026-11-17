# MindStella のセッションの作業の完了と停止を Discord に通知する

## 概要

利用者が、MindStella のセッションに依頼した作業が終わったこと・セッションが止まったことを、MindStella の画面を開かずに Discord のチャンネルで知れるようになる。

## 背景

[Issue #568](https://github.com/shuhei1101/mindstella/issues/568) の要望（検討事項 D-639 で案 A を選択。利用者の指定で最優先）。

- 利用者は、MindStella の画面を開いて確認するまで、AI の応答が終わったことに気付けない
- MindStella に、外部へ通知する仕組みは無い
- 通知を扱った [#157](https://github.com/shuhei1101/mindstella/issues/157) は、AI の書き込みを commit までステージングする範囲を含んでいて、対応しないでクローズした。この PR はその範囲を含まない
- 常駐サーバーは、MindStella のセッションのフックから応答の始まりと終わり・終了の出来事を受けている（インターフェース定義『MindStella のセッションの出来事の受け取り』）
- 利用上限・無操作の上限での停止の検知は [#520](https://github.com/shuhei1101/mindstella/issues/520)・[#521](https://github.com/shuhei1101/mindstella/issues/521) が作り、この PR の通知を呼ぶ

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 常駐サーバーの通知の計画書 |
| [反映作業](./反映作業/index.yaml) | 常駐サーバーに Webhook の設定のファイルを指定する作業 |
