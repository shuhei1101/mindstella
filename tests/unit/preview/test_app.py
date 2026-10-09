"""app.ts（起動・端末の保存領域・埋め込みのデータの読み込み）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 既定の設定
DEFAULT_PREFS = {"theme": None, "columns": {}, "look": None, "kinds": None, "diffSel": None}

# 表示する種類の全て（ワークスペースの既定も上書きも無いときに表示する種類）
ALL_KINDS = ["decisions", "docs", "logs", "notes", "research", "tasks", "terms"]

# 表の列の上書き（調査の表の列）
RESEARCH_COLUMNS = {"research": {"hidden": ["tags"], "pinTo": None}}

# `</script>` を JSON のエスケープ（バックスラッシュに続けて u003c・u003e）で持つ埋め込みの JSON
ESCAPED_JSON = '{"text": "\\u003c/script\\u003e"}'

# レビュー中のコメントを溜めた日時
CREATED = "2026-10-05T03:00:00+00:00"

# レビュー中のコメント（D-1 への 1 件・D-1 の本文の箇所を指す 1 件・T-1 への 1 件・項目を指さない 1 件）
COMMENT_ON_D1 = {
    "id": "C-1",
    "target": "D-1",
    "target_title": "問い",
    "loc": None,
    "body": "案 A にする",
    "created": CREATED,
}
COMMENT_ON_D1_BODY = {
    "id": "C-2",
    "target": "D-1",
    "target_title": "問い",
    "loc": {"kind": "body", "start": 5, "end": 5, "text": "五行目"},
    "body": "ここは言い換える",
    "created": CREATED,
}
COMMENT_ON_T1 = {
    "id": "C-3",
    "target": "T-1",
    "target_title": "作業",
    "loc": None,
    "body": "期日を決める",
    "created": CREATED,
}
COMMENT_ON_NOTHING = {
    "id": "C-4",
    "target": None,
    "target_title": None,
    "loc": None,
    "body": "全体に目を通した",
    "created": CREATED,
}


def test_read_embedded_data(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """要素の JSON を読む（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    html = f'<script type="application/json" id="mindmap-data">{ESCAPED_JSON}</script>'
    # 実行
    data = preview_page.evaluate(
        """(html) => {
            const doc = new DOMParser().parseFromString(html, "text/html");
            return MindmapPreview.readEmbeddedData(doc);
        }""",
        html,
    )
    # 検証
    assert data == {"text": "</script>"}


def test_read_embedded_data_when_empty(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """中身が空なら null（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    html = '<script type="application/json" id="mindmap-data"></script>'
    # 実行
    data = preview_page.evaluate(
        """(html) => {
            const doc = new DOMParser().parseFromString(html, "text/html");
            return MindmapPreview.readEmbeddedData(doc);
        }""",
        html,
    )
    # 検証
    assert data is None


def test_read_embedded_data_when_missing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """要素が無ければ送る（異常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    error = preview_page.evaluate(
        """() => {
            const doc = new DOMParser().parseFromString("<p></p>", "text/html");
            try {
                MindmapPreview.readEmbeddedData(doc);
            } catch (caught) {
                return {isError: caught instanceof Error, message: caught.message};
            }
            return null;
        }"""
    )
    # 検証
    assert error is not None
    assert error["isError"] is True
    assert error["message"] == "記録を読み込めませんでした。"


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        pytest.param(
            '{"theme": "dark", "columns": {}}', {**DEFAULT_PREFS, "theme": "dark"}, id="dark"
        ),
        pytest.param("{", DEFAULT_PREFS, id="broken_json"),
        pytest.param(None, DEFAULT_PREFS, id="storage_throws"),
        pytest.param(
            '{"look": "rainbow", "kinds": ["decisions", "graph"]}',
            DEFAULT_PREFS,
            id="unknown_look_and_kinds",
        ),
        pytest.param(
            '{"look": "dust", "kinds": ["tasks"]}',
            {**DEFAULT_PREFS, "look": "dust", "kinds": ["tasks"]},
            id="look_and_kinds",
        ),
    ],
)
def test_load_prefs(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: str | None,
    expected: dict[str, Any],
) -> None:
    """残した設定を読み、読めなければ既定（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    prefs = preview_page.evaluate(
        """(stored) => {
            // stored が null のときは、getItem が例外を送る保存領域にする
            const storage = {
                getItem: (key) => {
                    if (stored === null) throw new Error("保存領域が使えません");
                    return key === "mindmap-preview" ? stored : null;
                },
            };
            return MindmapPreview.loadPrefs(storage);
        }""",
        stored,
    )
    # 検証
    assert prefs == expected


# 保存する設定
SAVED_PREFS = {
    "theme": "dark",
    "columns": {"decisions": {"hidden": ["tags"], "pinTo": "id"}},
    "look": "dust",
    "kinds": ["tasks"],
    "diffSel": None,
}


@pytest.mark.parametrize(
    ("setitem_throws", "expected_saved", "expected_loaded"),
    [
        pytest.param(False, True, SAVED_PREFS, id="working_storage"),
        # 例外を送る保存領域では、読み戻した値は確かめない（偽を返し、例外を送らないことだけを確かめる）
        pytest.param(True, False, None, id="setitem_throws"),
    ],
)
def test_save_prefs(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    setitem_throws: bool,
    expected_saved: bool,
    expected_loaded: dict[str, Any] | None,
) -> None:
    """書けたかを返し、残した設定を読める。保存領域が例外を送っても例外を送らない（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行（savePrefs が例外を送ると evaluate が失敗する）
    result = preview_page.evaluate(
        """({prefs, setitemThrows}) => {
            const values = new Map();
            const storage = {
                getItem: (key) => values.get(key) ?? null,
                setItem: (key, value) => {
                    if (setitemThrows) throw new Error("保存領域が使えません");
                    values.set(key, value);
                },
            };
            const saved = MindmapPreview.savePrefs({storage, prefs});
            return {saved, loaded: MindmapPreview.loadPrefs(storage)};
        }""",
        {"prefs": SAVED_PREFS, "setitemThrows": setitem_throws},
    )
    # 検証
    assert result["saved"] is expected_saved
    assert expected_loaded is None or result["loaded"] == expected_loaded


@pytest.mark.parametrize(
    ("first", "second", "expected_same"),
    [
        pytest.param(["D-1", None], ["D-1", None], True, id="same_target"),
        pytest.param(
            ["D-1", None],
            ["D-1", {"kind": "body", "start": 2, "end": 2, "text": "文"}],
            False,
            id="location_differs",
        ),
        pytest.param(
            ["D-1", {"kind": "body", "start": 2, "end": 2, "text": "文"}],
            ["D-1", {"text": "文", "end": 2, "start": 2, "kind": "body"}],
            True,
            id="key_order_differs",
        ),
        pytest.param([None, None], ["D-1", None], False, id="no_target"),
    ],
)
def test_form_key(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    first: list[Any],
    second: list[Any],
    expected_same: bool,
) -> None:
    """同じ向けた先は同じキー、箇所が違えば別のキー（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    same = preview_page.evaluate(
        "([a, b]) => MindmapPreview.formKey(...a) === MindmapPreview.formKey(...b)",
        [first, second],
    )
    # 検証
    assert same is expected_same


@pytest.mark.parametrize(
    ("prefs", "display", "expected"),
    [
        pytest.param(
            {"theme": None, "columns": {}, "look": None, "kinds": None},
            None,
            {
                "look": "deep",
                "kinds": ALL_KINDS,
                "defaultLook": "deep",
                "defaultKinds": ALL_KINDS,
                "overrides": [],
            },
            id="no_override_no_default",
        ),
        pytest.param(
            {"theme": None, "columns": {}, "look": None, "kinds": None},
            {
                "network_look": "starlight",
                "visible_kinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
            },
            {
                "look": "starlight",
                "kinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
                "defaultLook": "starlight",
                "defaultKinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
                "overrides": [],
            },
            id="workspace_default",
        ),
        pytest.param(
            {"theme": "dark", "columns": RESEARCH_COLUMNS, "look": "dust", "kinds": None},
            {
                "network_look": "starlight",
                "visible_kinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
            },
            {
                "look": "dust",
                "kinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
                "defaultLook": "starlight",
                "defaultKinds": ["decisions", "docs", "logs", "research", "tasks", "terms"],
                "overrides": ["ネットワークの見た目", "ライト / ダーク", "表の列（調査）"],
            },
            id="override_look_theme_columns",
        ),
    ],
)
def test_resolve_display(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    prefs: dict[str, Any],
    display: dict[str, Any] | None,
    expected: dict[str, Any],
) -> None:
    """上書き → ワークスペースの既定 → 組み込みの既定の順に項目ごとに読み分ける（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行（Set は並びを揃えた配列にして返す）
    resolved = preview_page.evaluate(
        """({prefs, display}) => {
            const result = MindmapPreview.resolveDisplay(prefs, display ?? undefined);
            return {
                look: result.look,
                kinds: [...result.kinds].sort(),
                defaultLook: result.defaultLook,
                defaultKinds: [...result.defaultKinds].sort(),
                overrides: result.overrides,
            };
        }""",
        {"prefs": prefs, "display": display},
    )
    # 検証
    assert resolved == expected


def test_clear_overrides(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """上書きだけを外し、差分の時点は残す（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    prefs = {
        "theme": "dark",
        "columns": RESEARCH_COLUMNS,
        "look": "dust",
        "kinds": ["tasks"],
        "diffSel": "since",
    }
    # 実行
    result = preview_page.evaluate(
        """(prefs) => ({cleared: MindmapPreview.clearOverrides(prefs), original: prefs})""", prefs
    )
    # 検証
    assert result["cleared"] == {
        "theme": None,
        "columns": {},
        "look": None,
        "kinds": None,
        "diffSel": "since",
    }
    assert result["original"] == prefs


def test_comment_counts(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """項目ごとに数え、箇所を指すコメントも含め、項目を指さないコメントは数えない（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    items = [COMMENT_ON_D1, COMMENT_ON_D1_BODY, COMMENT_ON_T1, COMMENT_ON_NOTHING]
    # 実行
    counts = preview_page.evaluate("""(items) => MindmapPreview.commentCounts(items)""", items)
    # 検証
    assert counts == {"D-1": 2, "T-1": 1}


@pytest.mark.parametrize(
    "items",
    [
        pytest.param([], id="no_items"),
        pytest.param(
            [COMMENT_ON_NOTHING, {**COMMENT_ON_NOTHING, "id": "C-5"}], id="only_untargeted"
        ),
    ],
)
def test_comment_counts_when_empty(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, items: list[dict[str, Any]]
) -> None:
    """項目を指すコメントが無ければ空の対応を返す（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    counts = preview_page.evaluate("""(items) => MindmapPreview.commentCounts(items)""", items)
    # 検証
    assert counts == {}
