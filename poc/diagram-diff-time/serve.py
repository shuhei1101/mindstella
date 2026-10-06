"""実機での確認のため、見本のワークスペースを作り preview_url で配信したまま待つ。"""
import json, os, shutil, sys, time
from pathlib import Path
WT = Path("/mnt/c/Users/shuhe/repo/mindmap/.claude/worktrees/poc-preview-diagram-diff-time")
sys.path.insert(0, str(WT / "tests"))
from workspace_fixtures import McpServer

out = Path(sys.argv[1])
ws = out / "workspace"
if ws.exists():
    shutil.rmtree(ws)
s = McpServer(python=sys.executable, env={**os.environ, "PYTHONUTF8": "1"}, cwd=out)
def call(name, **kw):
    r = s.call(name, workspace=str(ws), **kw)
    if r.is_error:
        print("ERR", name, kw, r.text, flush=True)
    return r
call("init", settings={
    "summary": "要件出しのスキル mindmap を設計する", "playbooks": ["システム開発"], "target_label": "システム",
    "phases": ["目的", "要件", "構成"], "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
    "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
    "goal": {"phase": "構成", "summary": "作り始められる", "deliverables": [{"title": "YAML のスキーマ"}]}, "links": []})
long_body = "\n".join(f"本文の行 {i}。差分の印を確かめるための文。" for i in range(1, 1001))
nodes = "\n".join(f"  N{i}[ノード {i}] --> N{i+1}" for i in range(1, 50))
mer = "```mermaid\nflowchart TD\n" + nodes + "\n```\n"
for i in range(1, 8):
    body = (long_body + "\n\n" + mer) if i == 7 else f"検討事項 {i} の本文。\n\n" + ("```mermaid\nflowchart LR\n  A --> B\n```\n" if i == 3 else "")
    call("add", kind="decision", item={"title": f"検討事項 {i}", "phase": ["目的", "要件", "構成"][i % 3],
        "category": "データ構造", "tags": ["スキーマ"] if i % 2 else ["画面"], "body_markdown": body,
        "status": "未決定", "options": [{"key": "A", "content": "案 A"}, {"key": "B", "content": "案 B"}]})
for i in range(1, 4):
    call("add", kind="task", item={"title": f"タスク {i}", "kind": "作業", "status": ["未着手", "進行中", "完了"][i - 1], "body_markdown": f"タスク {i} の本文"})
call("add", kind="research", item={"title": "調査 1", "question": "何を調べたか", "body_markdown": "調査の本文"})
call("add", kind="doc", item={"title": "資料 1", "kind": "図", "deliverable": True, "status": "下書き", "body_markdown": "# 資料\n本文"})
call("add", kind="term", item={"title": "用語 1", "meaning": "用語の意味"})
call("add", kind="note", item={"title": "メモ 1", "content": "メモの中身"})
call("add", kind="log", item={"title": "会話ログ 1", "date": "2026-10-06", "body_markdown": "会話の本文"})
call("commit", summary="1 回目: 項目を足した")
call("update", id="D-7", item={"body_markdown": long_body.replace("行 500。", "行 500（直した）。") + "\n\n" + mer.replace("ノード 25", "ノード 25 改")})
call("update", id="D-3", item={"title": "検討事項 3（直した）"})
call("commit", summary="2 回目: 本文を直した")
call("update", id="D-7", item={"body_markdown": long_body.replace("行 10。", "行 10（再び直した）。") + "\n\n" + mer.replace("ノード 40", "ノード 40 改")})
call("adopt", id="D-5", key="A")
call("commit", summary="3 回目: 採用と本文")
r = call("preview_url")
print("URL", json.dumps(r.data, ensure_ascii=False), flush=True)
(out / "url.txt").write_text(r.data["url"] if r.data else "", encoding="utf-8")
while s.process.poll() is None and not (out / "stop").exists():
    time.sleep(2)
s.stop()
