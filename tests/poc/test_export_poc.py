"""PoC: React の画面の 1 枚の HTML を file:// でネット無しで開けるかを確かめる。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "poc"))
sys.path.insert(0, str(REPO / "plugins" / "mindstella" / "skills" / "mindmap" / "scripts"))

import builder  # noqa: E402
from inject import inject  # noqa: E402

BUILT = REPO / "poc" / "dist-export" / "index.html"
OUT_DIR = REPO / "poc" / "out"
MDMARK_REF = "develop"
SUMMARY = "PoC の話し合いの題"
BODY = """# 資料の本文

本文に </script> を含む

```mermaid
flowchart LR
  A[入口] --> B[出口]
```

<!-- map -->

```mermaid
flowchart LR
  X[構成の左] --> Y[構成の右]
```

<!-- /map -->
"""
TIMEOUT_MS = 20_000


@pytest.fixture(scope="module")
def built() -> Path:
    """書き出し用のビルドを作る。"""
    subprocess.run(["npx", "vite", "build", "-c", "poc/vite.export.config.ts"], cwd=REPO, check=True, capture_output=True)
    return BUILT


@pytest.fixture
def export_html(built: Path, make_workspace: Any, make_item: Any, valid_settings: dict[str, Any]) -> Path:
    """記録と描画のライブラリを差し込んだ 1 枚の HTML を返す。"""
    root = make_workspace(
        make_item("D-1", title="検討事項の題"),
        make_item("A-1", title="図を持つ資料"),
        settings={**valid_settings, "summary": SUMMARY},
        bodies={"A-1.mark.md": BODY},
    )
    data = builder.read_records(root, resolve=lambda _version: MDMARK_REF)
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "配る.html"
    inject(built=built, data=data, out=out, mdmark_ref=MDMARK_REF)
    return out


def _open(page: Page, url: str, blocked: list[str], errors: list[str]) -> None:
    """外部への要求を止め、エラーを集めて開く。"""
    page.route("http*://**", lambda route: (blocked.append(route.request.url), route.abort()))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(url)


@pytest.mark.parametrize("engine", ["chromium", "firefox"])
def test_export_poc(export_html: Path, engine: str) -> None:
    """概要・資料の本文と図・画面の移動・再読み込みが file:// でネット無しで動く。"""
    result: dict[str, Any] = {"browser": engine, "html_bytes": export_html.stat().st_size}
    blocked: list[str] = []
    errors: list[str] = []
    with sync_playwright() as p:
        browser = getattr(p, engine).launch()
        page = browser.new_page()
        _open(page, export_html.as_uri(), blocked, errors)
        page.get_by_text(SUMMARY).first.wait_for(timeout=TIMEOUT_MS)
        result["overview_url"] = page.url
        page.locator("#tile-open").get_by_text("検討事項の題").wait_for(timeout=TIMEOUT_MS)
        # 資料の詳細を開く（タブを移り、項目を開く）
        page.get_by_role("link", name="資料").first.click()
        page.wait_for_function("() => location.hash.includes('tab=docs')", timeout=TIMEOUT_MS)
        page.get_by_text("図を持つ資料").first.click()
        page.wait_for_function("() => location.hash.includes('id=A-1')", timeout=TIMEOUT_MS)
        page.get_by_text("資料の本文").first.wait_for(timeout=TIMEOUT_MS)
        page.wait_for_function("() => document.querySelectorAll('svg').length >= 2", timeout=TIMEOUT_MS)
        result["svg_count"] = page.evaluate("() => document.querySelectorAll('svg').length")
        result["map_text"] = page.get_by_text("構成の左").count()
        result["mermaid_text"] = page.get_by_text("入口").count()
        hash_before = page.evaluate("() => location.hash")
        page.reload()
        page.get_by_text("資料の本文").first.wait_for(timeout=TIMEOUT_MS)
        page.get_by_text("構成の左").first.wait_for(timeout=TIMEOUT_MS)
        result["hash_kept"] = page.evaluate("() => location.hash") == hash_before
        result["hash"] = hash_before
        # 埋め込みの要素が本文の </script> で閉じていない（JSON として読め、本文がそのまま入っている）
        result["embedded_body_intact"] = page.evaluate(
            "() => Object.values(JSON.parse(document.getElementById('mindmap-data').textContent).bodies).some((t) => t.includes('本文に </script> を含む'))"
        )
        if engine == "chromium":
            result["heap_used"] = page.evaluate("() => performance.memory.usedJSHeapSize")
        page.screenshot(path=str(OUT_DIR / f"{engine}.png"), full_page=True)
        browser.close()
    result["blocked"] = blocked
    result["errors"] = errors
    (OUT_DIR / f"{engine}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    assert blocked == []
    assert errors == []
    assert result["hash_kept"]
    assert result["map_text"] >= 1
    assert result["mermaid_text"] >= 1
    assert result["embedded_body_intact"]
