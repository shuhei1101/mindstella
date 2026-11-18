"""依存をたどって、影響と着手できる検討事項を出す（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from kinds import KINDS, Kind, id_number, kind_of_id
from store import Workspace, find_item, related_ids

# 種類 → 参照先から参照元へ逆向きにたどる関連の種類
IMPACT_KEYS: dict[Kind, tuple[str, ...]] = {
    "decision": ("depends_on", "parent"),
    "task": ("for", "depends_on"),
}

# ID → 項目の種類と中身
type ItemIndex = dict[str, tuple[Kind, dict[str, Any]]]

# 影響をたどるキー
type ImpactKey = Literal["depends_on", "parent", "for"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Affected:
    """影響の洗い出しの出力の `affected[]` の 1 行。"""

    id: str
    title: str
    status: str
    # 起点とこの項目の間にある項目の ID
    via: list[str]
    # 直前の項目とつなぐキー
    key: ImpactKey


def build_reverse_edges(workspace: Workspace) -> dict[str, list[tuple[str, str]]]:
    """参照先の ID → それを参照する項目とキーの並びを作る。"""
    edges: dict[str, list[tuple[str, str]]] = {}
    for kind, keys in IMPACT_KEYS.items():
        for item in workspace.items[kind]:
            related = item.get("related")
            # 参照元の並びはファイルの並び、同じ項目の中は related の並び
            for entry in related if isinstance(related, list) else []:
                if not isinstance(entry, dict) or entry.get("type") not in keys:
                    continue
                if isinstance(entry.get("to"), str):
                    edges.setdefault(entry["to"], []).append((item["id"], entry["type"]))
    return edges


def trace_impact(workspace: Workspace, start_id: str) -> list[Affected]:
    """起点から逆向きの参照を幅優先でたどり、影響を受ける項目を近い順に返す。"""
    # 起点があるか確かめる
    find_item(workspace, start_id)
    edges = build_reverse_edges(workspace)
    index = _index_items(workspace)
    # 起点から各項目までの途中の項目の ID（最初に届いた経路）
    via_of: dict[str, list[str]] = {start_id: []}
    visited = {start_id}
    frontier = [start_id]
    affected: list[Affected] = []
    while frontier:
        # 同じ距離で初めて届いた項目と、その直前の項目・キー
        found: dict[str, tuple[str, str]] = {}
        for current in frontier:
            for ref_id, key in edges.get(current, []):
                # 一度出た項目・ワークスペースに無い項目はたどらない
                if ref_id in visited or ref_id in found or ref_id not in index:
                    continue
                found[ref_id] = (current, key)
        # 同じ距離の中は ID の順に並べる
        frontier = sorted(found, key=_order_key)
        for node in frontier:
            parent, key = found[node]
            via_of[node] = [] if parent == start_id else [*via_of[parent], parent]
            item = index[node][1]
            affected.append(
                Affected(
                    id=node,
                    title=str(item.get("title", "")),
                    status=str(item.get("status", "")),
                    via=via_of[node],
                    key=cast(ImpactKey, key),
                )
            )
        visited.update(found)
    return affected


def is_settled(kind: Kind, item: dict[str, Any] | None) -> bool:
    """項目の状態がその種類の決着に当たるか。無い項目（None）は未完了として偽を返す。"""
    if item is None:
        return False
    return item.get("status") in KINDS[kind].settled_statuses


def list_ready(workspace: Workspace) -> list[str]:
    """前提が全て決着した未決定の検討事項の ID を、連番の小さい順に返す。"""
    index = _index_items(workspace)
    ready = [
        item["id"]
        for item in workspace.items["decision"]
        # 未決定で、前提（depends_on）が全て決着しているもの（無い ID は未完了）
        if item.get("status") == "未決定"
        and all(_is_id_settled(index, dep) for dep in related_ids(item, "depends_on"))
    ]
    return sorted(ready, key=id_number)


def _index_items(workspace: Workspace) -> ItemIndex:
    """ID → 項目の種類と中身の引き当て表を作る。"""
    return {
        item["id"]: (kind, item)
        for kind in KINDS
        for item in workspace.items[kind]
        if isinstance(item.get("id"), str)
    }


def _is_id_settled(index: ItemIndex, item_id: str) -> bool:
    """ID の項目が決着しているか。ワークスペースに無い ID は未完了として扱う。"""
    entry = index.get(item_id)
    return entry is not None and is_settled(entry[0], entry[1])


def _order_key(item_id: str) -> tuple[int, int]:
    """種類の順（D・T・R・A・G・N・L）→ 連番の順に並べるためのキーを返す。"""
    kind = kind_of_id(item_id)
    kind_rank = list(KINDS).index(kind) if kind is not None else len(KINDS)
    return (kind_rank, id_number(item_id))
