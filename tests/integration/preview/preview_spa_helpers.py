"""React のプレビュー（SPA）を開く結合テストの共通の関数。

`preview_url` が返した URL のオリジンの `/spa/` を開き、本文の区画に中身が入るまで待つ。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import ConsoleMessage, Error, Page

# SPA の入口のパス
SPA_ROOT_PATH = "/spa/"

# 本文の区画の中身（タイルか、記録を読めなかった表示）
SPA_CONTENT_SELECTOR = "main#main > div > *"

# SPA が描き終わるまで待つ上限ミリ秒
SPA_RENDER_TIMEOUT_MS = 15_000

# npm ci で入る axe-core の配布ファイル（リポジトリの直下からの位置）
AXE_SCRIPT = Path(__file__).resolve().parents[3] / "node_modules" / "axe-core" / "axe.min.js"

# 画面全体に WCAG 2.1 の A・AA の規則を当て、違反した規則と要素の目印を返す
AXE_WCAG_JS = """async () => {
  const result = await axe.run(document, {
    runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] },
  });
  return result.violations.flatMap((rule) => rule.nodes.map((node) => `${rule.id}: ${node.target.join(" ")}`));
}"""


@dataclass
class ConsoleErrors:
    """開いた画面のコンソールのエラーと、未処理の例外。"""

    messages: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)


def spa_url(preview_url: str, search: str = "") -> str:
    """`preview_url` が返した URL のオリジンの `/spa/` に search を付けた URL を返す。"""
    parts = urlsplit(preview_url)
    return f"{parts.scheme}://{parts.netloc}{SPA_ROOT_PATH}{search}"


def watch_console(page: Page) -> ConsoleErrors:
    """画面のコンソールのエラーと未処理の例外を集め始め、集めた先を返す。"""
    errors = ConsoleErrors()

    def _on_console(message: ConsoleMessage) -> None:
        """エラーのメッセージだけを残す。"""
        if message.type == "error":
            errors.messages.append(message.text)

    def _on_page_error(error: Error) -> None:
        """未処理の例外を残す。"""
        errors.exceptions.append(error.message)

    page.on("console", _on_console)
    page.on("pageerror", _on_page_error)
    return errors


def open_spa(page: Page, preview_url: str, search: str = "") -> Page:
    """SPA を開き、本文の区画に中身が入るのを待つ。"""
    page.goto(spa_url(preview_url, search))
    page.wait_for_selector(SPA_CONTENT_SELECTOR, state="attached", timeout=SPA_RENDER_TIMEOUT_MS)
    return page


def wcag_violations(page: Page) -> list[str]:
    """画面全体に WCAG 2.1 の A・AA の規則を当て、違反を `{規則}: {要素}` の行で返す。"""
    if not page.evaluate("typeof axe !== 'undefined'"):
        page.add_script_tag(path=str(AXE_SCRIPT))
    violations: list[str] = page.evaluate(AXE_WCAG_JS)
    return violations
