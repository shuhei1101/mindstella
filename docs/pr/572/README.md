# 新規ワークスペースの配信元の追加・指定したアカウントでの起動・前のバージョンの形式の問題の判定を修正する

## 概要

利用者が、配信元の行が無いワークスペースを `mindstella-dev` で作れ、アカウントを指定して起動するとそのアカウントで MindStella のセッションが起動するようにする。
あわせて、develop で fail する単体テスト `test_is_legacy_problem[decision]` を、モジュール構成『store.py』に合わせて pass させる。

## 背景

[#563](https://github.com/shuhei1101/mindstella/issues/563) は、[#531](https://github.com/shuhei1101/mindstella/pull/531)・[#540](https://github.com/shuhei1101/mindstella/pull/540)（常駐サーバーと MindStella のセッションへの作り直し）で入った退行 3 件の束で、v0.13.0 の release の前に修正する。

| Issue | 退行 |
| --- | --- |
| [#554](https://github.com/shuhei1101/mindstella/issues/554) | `project_index.add_source` が `POST /settings/sources` に `expectedVersion` を送信せず 400 になり、配信元の行が無いワークスペース（新規作成・フォルダを移した後）で起動が止まる |
| [#556](https://github.com/shuhei1101/mindstella/issues/556) | claude-balancer がある端末では `CLAUDE_CONFIG_DIR` を使用せず、指定したアカウントで起動しない（v0.12.1 までは指定したアカウントで起動していた） |
| [#561](https://github.com/shuhei1101/mindstella/issues/561) | `store.is_legacy_problem` が `D-1`（`status="完了"`）の問題を前のバージョンの形式と判定し、`test_is_legacy_problem[decision]` が fail する |

#556 の前提の [shuhei1101/claude-balancer#346](https://github.com/shuhei1101/claude-balancer/issues/346)（`exec --account`）は claude-balancer の develop に入っているが、タグはまだ無い（[shuhei1101/claude-balancer#358](https://github.com/shuhei1101/claude-balancer/issues/358)）。
ユーザーの指示（[#563 のコメント](https://github.com/shuhei1101/mindstella/issues/563#issuecomment-6968346846)）で、タグを待たずに develop の claude-balancer で確認して進める。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と変更箇所の由来 |
| [サーバー](./サーバー.md) | サーバーの計画書 |
