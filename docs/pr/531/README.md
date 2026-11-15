# 端末に 1 つの常駐サーバーと、ワークスペースと MindStella のセッションの作成・停止とクローズの API を作る

## 概要

外部のアプリ（aituber など）と端末の利用者が、MindStella の API でワークスペースと MindStella のセッションを作り、止めて、ワークスペースをクローズにできるようになる。
プラグインのコードが更新されたのに常駐サーバーが古いコードで動いているとき、利用者が気づけて再起動できるようになる。

## 背景

[Issue #516](https://github.com/shuhei1101/mindstella/issues/516) の要望で、MindStella を project-index と同じ作りに作り直す束 [Issue #481](https://github.com/shuhei1101/mindstella/issues/481) の子のうち、ほかの全ての子の前提になる 1 つ目（資料 A-107 の「シナリオを作る順」の No 1。シナリオは資料 A-115・A-116）。

- 今は起動スクリプト（`plugins/mindstella/bin/mindstella`）が tmux の中で Claude Code を立ち上げ、最初の入力は利用者が端末で行う。外部のアプリが、ワークスペースの作成と、MindStella のセッションの起動・停止を API で呼べない
- 常駐サーバーは SessionStart のフック（`ensure_server.py`）が落ちていれば起動する。`ensure_server.py` は常駐サーバーのバージョンと `version.ini` の文字列だけを比べるので、`version.ini` を変えない develop のコミットでプラグインが更新されても、常駐サーバーは古いフォルダのコードと画面を配信し続ける（2026-11-14 に #529 で起きた。[利用者の追記](https://github.com/shuhei1101/mindstella/issues/516#issuecomment-6878692111)・資料 D-478〜D-480）
- ワークスペースの配信元の行の登録・変更は、project-index の行の単位の API（[project-index#10](https://github.com/shuhei1101/project-index/issues/10)。[project-index#29](https://github.com/shuhei1101/project-index/pull/29) で develop へマージ済み）を使う

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [サーバー](./サーバー.md) | 常駐サーバー・MindStella の API・ワークスペースの管理・セッションの管理・起動のコマンドの計画書 |
| [プラグイン](./プラグイン.md) | MindStella のセッションのフックの計画書 |
| [スキル](./スキル.md) | セットアップのスキルのワークスペースの作成を API に合わせる計画書 |
| [反映作業](./反映作業/index.yaml) | claude-balancer の `clients` に `mindstella` を足す作業 |
