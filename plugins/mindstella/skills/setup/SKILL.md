---
name: setup
description: 話し合いを始める・再開するときに、新しいワークスペースを作るか既存のワークスペースの状況を示して、話し合いを進めるスキル session へ渡す
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, mcp__plugin_mindstella_mindstella__init, mcp__plugin_mindstella_mindstella__status, mcp__plugin_mindstella_mindstella__migrate, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/register.py:*)
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
| 登録の変更 | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/起動スクリプトの登録.md` | 利用者が、起動スクリプトの登録を変えたい・外したい・アカウントを足したいと伝えた（MCP のツールの有無によらない。最初に実行して終える） |
| ツールの確認 | mindstella の MCP のツール（`mcp__plugin_mindstella_mindstella__init`・`status`・`migrate`）があるかを見る。無ければ、ワークスペースに何も書かず、常駐サーバーが待ち受けていないことを示し、端末で `python3 {プラグインのフォルダ}/skills/mindmap/scripts/ensure_server.py` を叩いてから `/mcp` で mindstella につなぎ直し、スキルを呼び直すよう案内して止まる（以降は実行しない）。依存は `ensure_server.py` が確かめる | 毎回最初（登録の変更の依頼があるときを除く） |
| tmux の外 | 登録のスクリプトを `show` で呼ぶ。`in_tmux` が `false` で `registered` が `false` なら、`${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/起動スクリプトの登録.md` で登録を持ちかける（登録した後もそのまま続ける）。断られたときと登録済みのときは、プレビューから送ったコメントを Claude Code へ入力しないことを伝えて続ける | ツールの確認でツールがあった |
| 新しいワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/新しいワークスペース.md` | `{ワークスペースのフォルダ}/.mindstella/config.yaml` も、直下の `config.yaml`・`mindmap.yaml` も Read で読めない |
| 既存のワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/既存のワークスペース.md` | `{ワークスペースのフォルダ}/.mindstella/config.yaml` か、直下の `config.yaml`・`mindmap.yaml` を Read で読める |

## ツール

ワークスペースの読み書きは、mindstella の MCP のツール（`mcp__plugin_mindstella_mindstella__{ツール}`）で行い、`workspace` にワークスペースのフォルダを渡す。
Bash で起動するのは登録のスクリプト（`python3 ${CLAUDE_PLUGIN_ROOT}/skills/setup/scripts/register.py`）だけで、ワークスペースを触るスクリプトを Bash で起動しない。

| ツール | 使う引数 |
| --- | --- |
| `init` | `workspace`・`settings`（設定のオブジェクト。`summary`・`description`・`playbooks`・`target_label`・`phases`・`targets`・`categories`・`goal`・`links`。`description`・`goal`・`links` は任意） |
| `migrate` | `workspace`・`plan: true` |
| `status` | `workspace` |
