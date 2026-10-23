"""app.ts（起動・端末の保存領域・埋め込みのデータの読み込み）の単体テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 既定の設定
DEFAULT_PREFS = {
    "theme": None,
    "columns": {},
    "look": None,
    "kinds": None,
    "diffSel": None,
    "filters": {},
    "minimap": None,
    "bodyLayout": None,
    "tablePin": None,
    "tableHead": None,
    "tableStripes": None,
    "sectionFold": None,
}

# 表示する種類の全て（ワークスペースの既定も上書きも無いときに表示する種類）
ALL_KINDS = ["decisions", "docs", "logs", "notes", "research", "tasks", "terms"]

# 絞り込みの条件の上書き（タスクは状態を未着手だけにし、検討事項は画面の既定の条件のまま）
TASKS_FILTERS = {"status": ["未着手"]}
DECISIONS_DEFAULT_FILTERS = {"status": ["要見直し", "未決定", "未整理", "保留"]}

# 表の列の上書き（調査の表の列）
RESEARCH_COLUMNS = {"research": {"hidden": ["tags"], "pinTo": None}}

# `</script>` を JSON のエスケープ（バックスラッシュに続けて u003c・u003e）で持つ埋め込みの JSON
ESCAPED_JSON = '{"text": "\\u003c/script\\u003e"}'

# 「前回開いてから」の始まりを決める日時（前回開いた日時・サーバーが書いた今の日時・タブを開いた日時）
OPENED_A = "2026-10-04T13:05:00+00:00"
OPENED_B = "2026-10-05T09:00:00+00:00"
OPENED_NOW = "2026-10-05T09:30:00+00:00"

# 読んだ記録の先頭のまとまりの通し番号
HEAD_SEQ = 2

# メモリの上に作る `Storage`（`sessionStorage` の代わり）と、`post` の呼んだ回数を数える関数を作る
STORAGE_AND_POST_SCRIPT = """
const makeSession = (initial) => {
    const data = new Map(Object.entries(initial));
    return {
        getItem: (key) => (data.has(key) ? data.get(key) : null),
        setItem: (key, value) => { data.set(key, String(value)); },
        removeItem: (key) => { data.delete(key); },
        clear: () => { data.clear(); },
        key: () => null,
        length: 0,
    };
};
const makePost = (reply) => {
    const post = async () => { post.calls += 1; return reply; };
    post.calls = 0;
    return post;
};
"""

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
        pytest.param(
            '{"filters": {"tasks": {"status": ["未着手"]}}}',
            {**DEFAULT_PREFS, "filters": {"tasks": {"status": ["未着手"]}}},
            id="filters",
        ),
        pytest.param('{"filters": [1]}', DEFAULT_PREFS, id="invalid_filters"),
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


@pytest.mark.parametrize(
    ("stored", "expected_minimap"),
    [
        pytest.param('{"theme": "dark", "minimap": false}', False, id="false"),
        pytest.param('{"theme": "dark", "minimap": true}', None, id="true"),
        pytest.param('{"theme": "dark", "minimap": "no"}', None, id="not_boolean"),
        pytest.param('{"theme": "dark", "columns": {}}', None, id="previous_version"),
    ],
)
def test_load_prefs_when_minimap(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: str,
    expected_minimap: bool | None,
) -> None:
    """差分のミニマップの上書きは false だけを読む（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    prefs = preview_page.evaluate(
        """(stored) => {
            const storage = {getItem: (key) => (key === "mindmap-preview" ? stored : null)};
            return MindmapPreview.loadPrefs(storage);
        }""",
        stored,
    )
    # 検証（ほかの項目はそのまま読める）
    assert prefs == {**DEFAULT_PREFS, "theme": "dark", "minimap": expected_minimap}


@pytest.mark.parametrize(
    ("stored", "expected_body_layout"),
    [
        pytest.param('{"theme": "dark", "bodyLayout": "side"}', "side", id="side"),
        pytest.param('{"theme": "dark", "bodyLayout": "inline"}', None, id="inline"),
        pytest.param('{"theme": "dark", "bodyLayout": 1}', None, id="not_string"),
        pytest.param('{"theme": "dark", "columns": {}}', None, id="previous_version"),
    ],
)
def test_load_prefs_when_body_layout(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: str,
    expected_body_layout: str | None,
) -> None:
    """本文の差分の並べ方の上書きは side だけを読む（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    prefs = preview_page.evaluate(
        """(stored) => {
            const storage = {getItem: (key) => (key === "mindmap-preview" ? stored : null)};
            return MindmapPreview.loadPrefs(storage);
        }""",
        stored,
    )
    # 検証（ほかの項目はそのまま読める）
    assert prefs == {**DEFAULT_PREFS, "theme": "dark", "bodyLayout": expected_body_layout}


@pytest.mark.parametrize(
    ("stored", "expected_overrides"),
    [
        pytest.param(
            '{"theme": "dark", "tablePin": false, "tableHead": false,'
            ' "tableStripes": true, "sectionFold": false}',
            {"tablePin": False, "tableHead": False, "tableStripes": True, "sectionFold": False},
            id="differs_from_default",
        ),
        pytest.param(
            '{"theme": "dark", "tablePin": true, "tableHead": true,'
            ' "tableStripes": false, "sectionFold": true}',
            {},
            id="same_as_default",
        ),
        pytest.param(
            '{"theme": "dark", "tablePin": "no", "tableHead": "no",'
            ' "tableStripes": "no", "sectionFold": "no"}',
            {},
            id="not_boolean",
        ),
        pytest.param('{"theme": "dark", "columns": {}}', {}, id="previous_version"),
    ],
)
def test_load_prefs_when_body_view(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: str,
    expected_overrides: dict[str, bool],
) -> None:
    """本文の表とセクションの見せ方の上書きは、既定と違う値だけを読む（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    prefs = preview_page.evaluate(
        """(stored) => {
            const storage = {getItem: (key) => (key === "mindmap-preview" ? stored : null)};
            return MindmapPreview.loadPrefs(storage);
        }""",
        stored,
    )
    # 検証（ほかの項目はそのまま読める）
    assert prefs == {**DEFAULT_PREFS, "theme": "dark", **expected_overrides}


# 保存する設定
SAVED_PREFS = {
    "theme": "dark",
    "columns": {"decisions": {"hidden": ["tags"], "pinTo": "id"}},
    "look": "dust",
    "kinds": ["tasks"],
    "diffSel": None,
    "filters": {"tasks": TASKS_FILTERS},
    "minimap": None,
    "bodyLayout": None,
    "tablePin": None,
    "tableHead": None,
    "tableStripes": None,
    "sectionFold": None,
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
    ("first", "second", "expected_same"),
    [
        pytest.param([None, None, "TH-1"], [None, None, "TH-1"], True, id="same_thread"),
        pytest.param([None, None, "TH-1"], [None, None, "TH-2"], False, id="other_thread"),
        pytest.param([None, None, "TH-1"], [None, None], False, id="new_thread_form"),
    ],
)
def test_form_key_when_thread(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    first: list[Any],
    second: list[Any],
    expected_same: bool,
) -> None:
    """スレッドごとに別のキーで、新しいスレッドの入力とも別（正常系）。"""
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
            {"theme": None, "columns": {}, "look": None, "kinds": None, "filters": {}},
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
            {"theme": None, "columns": {}, "look": None, "kinds": None, "filters": {}},
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
            {
                "theme": "dark",
                "columns": RESEARCH_COLUMNS,
                "look": "dust",
                "kinds": None,
                "filters": {},
            },
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
        pytest.param(
            {
                "theme": None,
                "columns": {},
                "look": None,
                "kinds": None,
                "filters": {"tasks": TASKS_FILTERS, "decisions": DECISIONS_DEFAULT_FILTERS},
            },
            None,
            {
                "look": "deep",
                "kinds": ALL_KINDS,
                "defaultLook": "deep",
                "defaultKinds": ALL_KINDS,
                "overrides": ["絞り込み（タスク）"],
            },
            id="override_filters",
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


@pytest.mark.parametrize(
    ("prefs", "expected"),
    [
        pytest.param(
            {**DEFAULT_PREFS, "minimap": None},
            {"minimap": True, "overrides": []},
            id="no_override",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "minimap": False},
            {"minimap": False, "overrides": ["差分のミニマップ"]},
            id="minimap_hidden",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "theme": "dark", "minimap": False},
            {"minimap": False, "overrides": ["ライト / ダーク", "差分のミニマップ"]},
            id="theme_and_minimap_hidden",
        ),
    ],
)
def test_resolve_display_when_minimap(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    prefs: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """差分のミニマップは上書きが false のときだけ偽で、変えている項目の末尾に並ぶ（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行（Set は並びを揃えた配列にして返す）
    resolved = preview_page.evaluate(
        """(prefs) => {
            const result = MindmapPreview.resolveDisplay(prefs, undefined);
            return {
                look: result.look,
                kinds: [...result.kinds].sort(),
                minimap: result.minimap,
                overrides: result.overrides,
            };
        }""",
        prefs,
    )
    # 検証（見た目と表示する種類は既定のまま）
    assert resolved == {"look": "deep", "kinds": ALL_KINDS, **expected}


@pytest.mark.parametrize(
    ("prefs", "expected"),
    [
        pytest.param(
            {**DEFAULT_PREFS, "bodyLayout": None},
            {"bodyLayout": "inline", "overrides": []},
            id="no_override",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "bodyLayout": "side"},
            {"bodyLayout": "side", "overrides": ["本文の差分の並べ方"]},
            id="side",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "minimap": False, "bodyLayout": "side"},
            {"bodyLayout": "side", "overrides": ["差分のミニマップ", "本文の差分の並べ方"]},
            id="minimap_hidden_and_side",
        ),
    ],
)
def test_resolve_display_when_body_layout(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    prefs: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """本文の差分の並べ方は上書きが side のときだけ side で、変えている項目の末尾に並ぶ（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    resolved = preview_page.evaluate(
        """(prefs) => {
            const result = MindmapPreview.resolveDisplay(prefs, undefined);
            return {bodyLayout: result.bodyLayout, overrides: result.overrides};
        }""",
        prefs,
    )
    # 検証
    assert resolved == expected


@pytest.mark.parametrize(
    ("prefs", "expected"),
    [
        pytest.param(
            DEFAULT_PREFS,
            {
                "bodyView": {"pin": True, "head": True, "stripes": False, "fold": True},
                "overrides": [],
            },
            id="no_override",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "tableStripes": True, "sectionFold": False},
            {
                "bodyView": {"pin": True, "head": True, "stripes": True, "fold": False},
                "overrides": ["表のしま模様", "セクションの折りたたみ"],
            },
            id="stripes_on_fold_off",
        ),
        pytest.param(
            {**DEFAULT_PREFS, "minimap": False, "tablePin": False, "bodyLayout": "side"},
            {
                "bodyView": {"pin": False, "head": True, "stripes": False, "fold": True},
                "overrides": ["差分のミニマップ", "表の列の固定", "本文の差分の並べ方"],
            },
            id="between_minimap_and_body_layout",
        ),
    ],
)
def test_resolve_display_when_body_view(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    prefs: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    """本文の見せ方は上書きのある項目だけ既定と逆にし、変えている項目に差分のミニマップと本文の差分の並べ方の間で並ぶ（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    resolved = preview_page.evaluate(
        """(prefs) => {
            const result = MindmapPreview.resolveDisplay(prefs, undefined);
            return {bodyView: result.bodyView, overrides: result.overrides};
        }""",
        prefs,
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
        "filters": {"tasks": TASKS_FILTERS},
        "minimap": False,
        "bodyLayout": "side",
        "tablePin": False,
        "tableHead": False,
        "tableStripes": True,
        "sectionFold": False,
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
        "filters": {},
        "minimap": None,
        "bodyLayout": None,
        "tablePin": None,
        "tableHead": None,
        "tableStripes": None,
        "sectionFold": None,
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


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        pytest.param(
            {
                "previous": {"at": OPENED_A, "seq": 1},
                "opened": {"at": OPENED_B, "seq": HEAD_SEQ},
            },
            {"at": OPENED_A, "seq": 1},
            id="previous_kept",
        ),
        pytest.param(
            {"previous": None, "opened": {"at": OPENED_B, "seq": HEAD_SEQ}},
            {"at": OPENED_B, "seq": HEAD_SEQ},
            id="no_previous",
        ),
        pytest.param(
            {
                "previous": {"at": OPENED_A, "seq": 5},
                "opened": {"at": OPENED_B, "seq": HEAD_SEQ},
            },
            {"at": OPENED_B, "seq": HEAD_SEQ},
            id="previous_seq_ahead",
        ),
        pytest.param(None, {"at": OPENED_NOW, "seq": HEAD_SEQ}, id="unreachable"),
    ],
)
def test_resolve_since(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    reply: dict[str, Any] | None,
    expected: dict[str, Any],
) -> None:
    """サーバーの配信では前回の時点を始まりにし、無い・通し番号が先のときは今の時点にする（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    result = preview_page.evaluate(
        STORAGE_AND_POST_SCRIPT
        + """async ({reply, headSeq, now}) => {
            const session = makeSession({});
            const since = await MindmapPreview.resolveSince({
                serverMode: true,
                prefs: {},
                persist: () => undefined,
                headSeq,
                session,
                post: makePost(reply),
                now: () => now,
            });
            return {since, kept: session.getItem(MindmapPreview.SINCE_KEY)};
        }""",
        {"reply": reply, "headSeq": HEAD_SEQ, "now": OPENED_NOW},
    )
    # 検証
    assert result["since"] == expected
    assert json.loads(result["kept"]) == expected


@pytest.mark.parametrize(
    ("kept", "expected_calls", "expected"),
    [
        pytest.param(
            json.dumps({"at": OPENED_A, "seq": 1}),
            0,
            {"at": OPENED_A, "seq": 1},
            id="point_kept",
        ),
        pytest.param(OPENED_A, 1, {"at": OPENED_A, "seq": 1}, id="previous_version_kept"),
    ],
)
def test_resolve_since_when_kept(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    kept: str,
    expected_calls: int,
    expected: dict[str, Any],
) -> None:
    """同じタブに残した始まりを使い、前の版の値は使わない（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    reply = {
        "previous": {"at": OPENED_A, "seq": 1},
        "opened": {"at": OPENED_B, "seq": HEAD_SEQ},
    }
    # 実行
    result = preview_page.evaluate(
        STORAGE_AND_POST_SCRIPT
        + """async ({kept, reply, headSeq, now}) => {
            const post = makePost(reply);
            const since = await MindmapPreview.resolveSince({
                serverMode: true,
                prefs: {},
                persist: () => undefined,
                headSeq,
                session: makeSession({[MindmapPreview.SINCE_KEY]: kept}),
                post,
                now: () => now,
            });
            return {since, calls: post.calls};
        }""",
        {"kept": kept, "reply": reply, "headSeq": HEAD_SEQ, "now": OPENED_NOW},
    )
    # 検証
    assert result == {"since": expected, "calls": expected_calls}


@pytest.mark.parametrize(
    ("opened", "expected"),
    [
        pytest.param(
            {"at": OPENED_A, "seq": 1}, {"at": OPENED_A, "seq": 1}, id="point"
        ),
        pytest.param(OPENED_A, {"at": OPENED_NOW, "seq": HEAD_SEQ}, id="previous_version"),
        pytest.param(None, {"at": OPENED_NOW, "seq": HEAD_SEQ}, id="missing"),
    ],
)
def test_resolve_since_when_exported(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    opened: dict[str, Any] | str | None,
    expected: dict[str, Any],
) -> None:
    """配る書き出しは端末の設定の前回の時点を使い、今の時点に書き換える（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    prefs = {**DEFAULT_PREFS} if opened is None else {**DEFAULT_PREFS, "opened": opened}
    # 実行
    result = preview_page.evaluate(
        STORAGE_AND_POST_SCRIPT
        + """async ({prefs, headSeq, now}) => {
            let persisted = 0;
            const post = makePost(null);
            const since = await MindmapPreview.resolveSince({
                serverMode: false,
                prefs,
                persist: () => { persisted += 1; },
                headSeq,
                session: makeSession({}),
                post,
                now: () => now,
            });
            return {since, opened: prefs.opened, persisted, calls: post.calls};
        }""",
        {"prefs": prefs, "headSeq": HEAD_SEQ, "now": OPENED_NOW},
    )
    # 検証
    assert result == {
        "since": expected,
        "opened": {"at": OPENED_NOW, "seq": HEAD_SEQ},
        "persisted": 1,
        "calls": 0,
    }
