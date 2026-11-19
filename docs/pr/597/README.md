# ワークスペースと MindStella のセッションの状態を、何も書き換えずに取得できるようにする（GET /workspaces/{id}・GET /workspaces）

## 概要

外部のアプリ（aituber など）と利用者が、ワークスペースと MindStella のセッションの状態とワークスペースの一覧を、何も書き換えずに取得し、停止の完了の確認・活動の期限の判断・開き直すかの判断に使用できるようになる。

## 背景

[Issue #522](https://github.com/shuhei1101/mindstella/issues/522) の要望（[#481](https://github.com/shuhei1101/mindstella/issues/481) の子。資料 A-107 の「シナリオを作る順」の No 7。シナリオは資料 A-126、API の原本は資料 A-119 の「MindStella の API」の表）。

- MindStella の API は、ワークスペースの作成・MindStella のセッションの作成・一覧・停止・起動し直し・クローズを持つ。ワークスペースの状態（`GET /workspaces/{id}`）とワークスペースの一覧（`GET /workspaces`）は資料 A-119 で決めたが未実装
- 今の『MindStella のセッションの一覧』は、状態に起動中とあってペインかプロセスが無ければ、落ちたとして状態を書き換えて『停止の通知』を呼ぶ。資料 A-126 は、状態の取得は何も書き換えないと決めている。落ちたことの記録と通知は、[#582](https://github.com/shuhei1101/mindstella/pull/582) で入った落ちたことの見回りも行う
- 追加の MCP・プラグインの記録（`launch.json`）が無いときの警告は、[#582](https://github.com/shuhei1101/mindstella/pull/582) で作成と起動し直しの応答に入った。状態の取得に記録の有無を含めることは資料 A-119 で決めている（[受付判断のレビュー](https://github.com/shuhei1101/mindstella/issues/522#issuecomment-6853194342) の任意の指摘で、この Issue で作ると決めた）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 常駐サーバーの状態の取得・ワークスペースの一覧・MindStella の MCP のツールの計画書 |
