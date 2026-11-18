# MindStella のセッションを自動で起動し直し、利用上限では別のアカウントで会話を引き継いで再開する

## 概要

利用者が、MindStella のセッションが利用上限に達した・落ちた・止まった後も、リセットを待たずに同じ会話の続きから話し合いを続けられるようになる。

## 背景

[Issue #520](https://github.com/shuhei1101/mindstella/issues/520) の要望（[#481](https://github.com/shuhei1101/mindstella/issues/481) の子。資料 A-107 の「シナリオを作る順」の No 5）と、利用者の追記（[追記のコメント](https://github.com/shuhei1101/mindstella/issues/520#issuecomment-6963450998)。利用者の指定で急ぎ）。

- MindStella のセッションは claude-balancer で借りたアカウントで起動する。借りたアカウントが利用上限に達すると、セッションは止まったままになり、リセットまで MindStella を使用できない
- AI Monitor は、利用上限に達したエージェントを止め、claude-balancer から別のアカウントを借り直して同じ会話から再開する。MindStella には、この動きが無い
- 今の『MindStella のセッションの作成』は、停止済み・落ちている MindStella のセッションを無いものとして扱い、新規の会話で起動する。状態のフォルダの `session.json` は Claude Code の `session_id` を持つが、起動し直しで使用していない
- 起動し直しの API（`POST /workspaces/{id}/sessions/{session}/restart`）・コメントが届いたときの起動し直し・PreCompact と StopFailure のフックでの起動し直しは、資料 A-119 で決めたが未実装
- 止まったことの Discord への通知は [#570](https://github.com/shuhei1101/mindstella/issues/570)（PR [#571](https://github.com/shuhei1101/mindstella/pull/571)）で入り、利用上限での停止はこの PR が通知を呼ぶ

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 常駐サーバーの起動し直し・利用上限での借り直し・会話の引き継ぎの計画書 |
| [プラグイン](./プラグイン.md) | PreCompact のフックの登録の計画書 |
