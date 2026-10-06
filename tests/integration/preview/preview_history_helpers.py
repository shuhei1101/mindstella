"""差分の表示の結合テストが共有する、変更履歴つきのワークスペースの作り方と値。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from workspace_fixtures import RECORD_DIR

__all__ = [
    "BODY_A1_AFTER",
    "BODY_A1_BEFORE",
    "BODY_D1_AFTER",
    "BODY_D1_BEFORE",
    "HISTORY_SELS",
    "assert_topbar_history",
    "build_history_workspace",
    "build_long_line_diff_workspace",
    "preselect_diff",
    "read_yaml",
]

# 差分の表示で選べる時点の識別子
HISTORY_SELS = {"since": "since", "pending": "pending", "second": "V-2", "first": "V-1"}

# 検討事項 D-1 の書き換える前の本文（段落・表・flowchart の図を持つ）
BODY_D1_BEFORE = """# 概要

最初の段落です。

次の段落を消します。

| 列 A | 列 B |
| --- | --- |
| 1 | 2 |
| 3 | 4 |
| 5 | 6 |

```mermaid
flowchart TD
  A[開始] --> B_1[処理]
  B_1 --> C[終了]
```

最後の段落です。
"""

# D-1 の書き換えた後の本文（段落を消して足し、表の行を消して足し、図のノードを変えて足す）
BODY_D1_AFTER = """# 概要

最初の段落です。

新しい段落を足しました。

| 列 A | 列 B |
| --- | --- |
| 1 | 2 |
| 5 | 6 |
| 7 | 8 |

```mermaid
flowchart TD
  A[開始] --> B_1[処理を変えた]
  B_1 --> D[追加]
```

最後の段落です。
"""

# 資料 A-1 の書き換える前と後の本文（色を付けない種類の gantt の図）
BODY_A1_BEFORE = """# 工程

```mermaid
gantt
  dateFormat YYYY-MM-DD
  section 準備
  設計 :a1, 2026-10-01, 3d
```
"""
BODY_A1_AFTER = """# 工程

```mermaid
gantt
  dateFormat YYYY-MM-DD
  section 準備
  設計 :a1, 2026-10-01, 3d
  実装 :a2, after a1, 5d
```
"""

# 検討事項 D-2 の本文（V-2 で 1 行直し、まとめる前にもう一度、頭に段落を足して行をずらす）
BODY_D2_V1 = "1 行目の段落\n\n2 つ目の段落\n"
BODY_D2_V2 = "1 行目の段落\n\n書き換えた 2 つ目の段落\n"
BODY_D2_NOW = "頭に足した段落\n\n1 行目の段落\n\n書き換えた 2 つ目の段落\n"

# まとまり V-1・V-2 の日時と、前回開いた日時（V-1 と V-2 の間）
FIRST_SET_AT = "2026-10-01T00:00:00+00:00"
SECOND_SET_AT = "2026-10-02T00:00:00+00:00"
OPENED_AT = "2026-10-01T12:00:00+00:00"


def read_yaml(path: Path) -> Any:
    """YAML を読む。"""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _call(call_tool: Any, name: str, **arguments: Any) -> dict[str, Any]:
    """ツールを呼び、エラーならテストを止めて結果を返す。"""
    result = call_tool(name, **arguments)
    assert result.is_error is False, result.text
    return result.data


def build_history_workspace(
    make_workspace: Any, call_tool: Any, *, pending: bool = True, history_limit: int | None = None
) -> Path:
    """実際のツールで、まとまり 2 つ（V-1 で足し、V-2 で直す）と、まとめていない変更を持つワークスペースを作る。"""
    root: Path = make_workspace()
    if history_limit is not None:
        settings = read_yaml(root / RECORD_DIR / "config.yaml")
        settings["history_limit"] = history_limit
        (root / RECORD_DIR / "config.yaml").write_text(
            yaml.safe_dump(settings, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    workspace = str(root)
    decision = {
        "title": "キーを種類ごとに分けるか",
        "status": "未決定",
        "answer": "旧い答え",
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    _call(call_tool, "add", workspace=workspace, kind="decision", item={**decision, "body_markdown": BODY_D1_BEFORE})
    _call(
        call_tool,
        "add",
        workspace=workspace,
        kind="decision",
        item={**decision, "title": "本文を後で直す問い", "answer": "答え", "body_markdown": BODY_D2_V1},
    )
    _call(
        call_tool,
        "add",
        workspace=workspace,
        kind="doc",
        item={"title": "工程の資料", "kind": "図", "deliverable": False, "status": "下書き", "body_markdown": BODY_A1_BEFORE},
    )
    _call(call_tool, "add", workspace=workspace, kind="task", item={"title": "決める", "kind": "作業", "status": "未着手"})
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    _call(
        call_tool,
        "update",
        workspace=workspace,
        id="D-1",
        item={"status": "決定済み", "answer": "新しい答え", "body_markdown": BODY_D1_AFTER},
    )
    _call(call_tool, "update", workspace=workspace, id="D-2", item={"body_markdown": BODY_D2_V2})
    _call(call_tool, "update", workspace=workspace, id="A-1", item={"body_markdown": BODY_A1_AFTER})
    _call(call_tool, "commit", workspace=workspace, summary="決める")
    if pending:
        _call(call_tool, "update", workspace=workspace, id="D-2", item={"body_markdown": BODY_D2_NOW})
        _call(call_tool, "update", workspace=workspace, id="T-1", item={"status": "進行中"})
        _call(call_tool, "add", workspace=workspace, kind="note", item={"title": "新しいメモ", "content": "メモ"})
    # まとまりの日時を固定し、前回開いた日時を V-1 と V-2 の間に置く
    changes = read_yaml(root / RECORD_DIR / "changes.yaml")
    changes["sets"][1]["at"] = FIRST_SET_AT
    changes["sets"][0]["at"] = SECOND_SET_AT
    (root / RECORD_DIR / "changes.yaml").write_text(
        yaml.safe_dump(changes, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (root / RECORD_DIR / ".mindstella-opened").write_text(f"{OPENED_AT}\n", encoding="utf-8")
    return root


def preselect_diff(page: Page, sel: str | None) -> None:
    """ページを開く前に、端末の保存領域へ選んだ時点を入れる（開いたときから差分の表示にする）。"""
    value = json.dumps({"diffSel": sel})
    page.add_init_script(
        f"try {{ if (!sessionStorage.getItem('mindmap-seeded')) {{ localStorage.setItem('mindmap-preview', {json.dumps(value)}); sessionStorage.setItem('mindmap-seeded', '1'); }} }} catch (e) {{}}"
    )


def assert_topbar_history(page: Page) -> None:
    """トップバーに「変更履歴」のボタンがあり、差分の表示の間は選んだ時点の札と外す × が右に並ぶ。"""
    history = page.get_by_role("button", name="変更履歴")
    assert history.get_attribute("aria-haspopup") == "dialog"
    chip = page.locator(".df-chip")
    assert chip.count() == 1
    assert chip.get_by_role("button", name="差分の表示をやめる").count() == 1
    history_box = history.bounding_box()
    chip_box = chip.bounding_box()
    assert history_box is not None
    assert chip_box is not None
    assert history_box["x"] + history_box["width"] <= chip_box["x"]


def build_long_line_diff_workspace(make_workspace: Any, call_tool: Any, long_line: str) -> Path:
    """実際のツールで、図に長い行を 1 行足したまとまり V-2 を持つ検討事項 D-1 のワークスペースを作る。"""
    root: Path = make_workspace()
    workspace = str(root)
    decision = {
        "title": "長い行を足す問い",
        "status": "未決定",
        "weight": "大",
        "category": "データ構造",
        "phase": "要件",
        "target": "mindmap",
    }
    before = "# 概要\n\n```mermaid\nflowchart LR\n  A --> B\n```\n"
    after = f"# 概要\n\n```mermaid\nflowchart LR\n  A --> B\n  B --> C[{long_line}]\n```\n"
    _call(call_tool, "add", workspace=workspace, kind="decision", item={**decision, "body_markdown": before})
    _call(call_tool, "commit", workspace=workspace, summary="最初の書き込み")
    _call(call_tool, "update", workspace=workspace, id="D-1", item={"body_markdown": after})
    _call(call_tool, "commit", workspace=workspace, summary="長い行を足す")
    return root
