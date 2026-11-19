# クローズしたワークスペースを開き直し、不要になったワークスペースを状態の記録ごと削除できるようにする（POST /workspaces/{id}/reopen・DELETE /workspaces/{id}）

## 概要

外部のアプリ（aituber など）と利用者が、クローズしたワークスペースを開き直して同じ進め方の文書・追加の MCP・プラグインで MindStella のセッションを作り直し、不要になったワークスペースを状態の記録ごと削除できるようになる。

## 背景

[Issue #523](https://github.com/shuhei1101/mindstella/issues/523) の要望（[#481](https://github.com/shuhei1101/mindstella/issues/481) の子。資料 A-107 の「シナリオを作る順」の No 8。API の原本は資料 A-119 の「MindStella の API」の表、クローズの後の扱いは資料 A-116 の `notes.開き直し`）。

- MindStella の API は、ワークスペースの作成・状態の取得・一覧・MindStella のセッションの作成・一覧・停止・起動し直し・クローズを持つ。開き直し（`POST /workspaces/{id}/reopen`）と削除（`DELETE /workspaces/{id}`）は資料 A-119 で決めたが未実装
- 今は、クローズしたワークスペースを戻す手段が同じフォルダでのワークスペースの作成だけで、クローズ待ちだけを解く手段も無い。削除の手段は無く、配信元の行と状態のフォルダの記録が残り続ける
- aituber の制作の削除（資料 A-132）は、前の試行で MindStella の側だけ削除済みのときに、`DELETE /workspaces/{id}` の「ワークスペースが無い」エラーを成功として扱う（[利用者の追記](https://github.com/shuhei1101/mindstella/issues/481#issuecomment-6852198736)）

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理 |
| [サーバー](./サーバー.md) | 常駐サーバーの開き直し・削除・MindStella の MCP のツールの計画書 |
