"""axe-core でアクセシビリティの規則を確かめる関数。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page

__all__ = ["axe_rule_results"]

# npm ci で入る axe-core の配布ファイル（リポジトリの直下からの位置）
AXE_SCRIPT = Path(__file__).resolve().parents[3] / "node_modules" / "axe-core" / "axe.min.js"

# 範囲と規則を絞って axe を走らせ、違反と通過した要素の目印を返す
AXE_RUN_JS = """async ([selector, rule]) => {
  const result = await axe.run({ include: [[selector]] }, { runOnly: { type: "rule", values: [rule] } });
  const marks = (items) => items.flatMap((item) => item.nodes.map((node) => node.target.join(" ")));
  return { violations: marks(result.violations), passes: marks(result.passes) };
}"""


def axe_rule_results(page: Page, selector: str, rule: str) -> dict[str, Any]:
    """`selector` の範囲だけに axe の規則 `rule` を当て、`violations`（違反）と `passes`（通過）の要素の目印を返す。"""
    if not page.evaluate("typeof axe !== 'undefined'"):
        page.add_script_tag(path=str(AXE_SCRIPT))
    result: dict[str, Any] = page.evaluate(AXE_RUN_JS, [selector, rule])
    return result
