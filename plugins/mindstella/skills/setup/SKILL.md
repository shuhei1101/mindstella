---
name: setup
description: 話し合いを始める・再開するときに、新しいワークスペースを作るか既存のワークスペースの状況を示して、話し合いを進めるスキル session へ渡す
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, mcp__mindstella__init, mcp__mindstella__status, mcp__mindstella__migrate
---

# setup

新しいワークスペースを作るか、既存のワークスペースの状況を示して、`/mindstella:session` へ渡す。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空ならフォルダの指定を尋ねて終える

## ステップ

上から順に進む。

| ステップ | 手順 | 実行する条件 |
| --- | --- | --- |
| ツールの確認 | mindstella の MCP のツール（`mcp__mindstella__init`・`status`・`migrate`）があるかを見る。無ければ、ワークスペースに何も書かず、起動スクリプト（`{プラグインのフォルダ}/bin/mindstella {ワークスペースのフォルダ}`）で立ち上げ直すよう案内して止まる（以降は実行しない）。依存は起動スクリプトが確かめる | 毎回最初 |
| 新しいワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/新しいワークスペース.md` | `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読めない |
| 既存のワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/既存のワークスペース.md` | `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読める |

## ツール

どれも mindstella の MCP のツール（`mcp__mindstella__{ツール}`）で、`workspace` にワークスペースのフォルダを渡す。
スクリプトを Bash で起動しない。

| ツール | 使う引数 |
| --- | --- |
| `init` | `workspace`・`settings`（設定のオブジェクト。`summary`・`description`・`playbooks`・`target_label`・`phases`・`targets`・`categories`・`goal`・`links`。`description`・`goal`・`links` は任意） |
| `migrate` | `workspace`・`plan: true` |
| `status` | `workspace` |
