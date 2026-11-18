# MindStella のセッションが止まったときも Discord に通知する

## 概要

利用者が、MindStella のセッションが止まったこと（エラー・停止の依頼）とその理由を、MindStella の画面を開かずに Discord のチャンネルで知れるようになる。

## 背景

[Issue #570](https://github.com/shuhei1101/mindstella/issues/570) の要望。

- [Issue #568](https://github.com/shuhei1101/mindstella/issues/568) は作業の完了と停止の通知を求めていた。利用者の判断で、作業 PR [#569](https://github.com/shuhei1101/mindstella/pull/569) は作業の完了の通知だけを作り、止まったときの通知をこの Issue へ分けた
- [#569](https://github.com/shuhei1101/mindstella/pull/569) で、Discord の Webhook へ送信する通知のモジュールと、Webhook の設定（環境変数 `MINDSTELLA_DISCORD_WEBHOOK_FILE`）を作った。この PR はそれを再利用する
- 今ある停止は、外部のアプリからの停止の依頼（インターフェース定義『MindStella のセッションの停止』）と、ペイン・プロセスが無くなったことの検知（落ちた）と、SessionEnd の出来事（インターフェース定義『MindStella のセッションの出来事の受け取り』）
- 利用上限・無操作の上限の停止はまだ無く、それを作る [#520](https://github.com/shuhei1101/mindstella/issues/520)・[#521](https://github.com/shuhei1101/mindstella/issues/521) が、この PR の通知を呼ぶ（計画の受付判断）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 常駐サーバーの停止の通知の計画書 |
