"""プレビューの単体テスト（フロント）の共通 fixture。

tsc が `.ts` から生成した `.js` を `page.add_script_tag` で読み、`page.evaluate` で関数を呼ぶ。
"""

from __future__ import annotations

import base64
import hashlib
import re
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml
from playwright.sync_api import Page

from .fixture_types import (
    LoadLibrary,
    LoadMdmark,
    LoadPreviewScripts,
    LoadPreviewStyles,
    MakeData,
    MdmarkDist,
    PutEmbeddedMdmark,
    PutMdmarkCss,
    PutMdmarkImportMap,
    ServeMdmark,
)

# このファイルから見たリポジトリの直下（tests/unit/preview の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# tsc が生成した `.js` を置くフォルダ
PREVIEW_DIR = REPO_ROOT / "plugins" / "mindstella" / "skills" / "mindmap" / "preview"

# 画面に当てる CSS（読む順）
STYLE_FILES = ("tokens.css", "style.css")

# 描画のライブラリの外部ライブラリの設計書を置くフォルダ
LIBRARY_DESIGN_DIR = REPO_ROOT / "dev" / "設計書" / "外部ライブラリ"

# テストのページを開く、仮のオリジン（history.pushState が使える http(s) の URL）
PAGE_URL = "https://preview.test/index.html"

# 起動する `.js`（差し込む順の最後で、読むと画面を描き始めるため、画面の部品のテストでは読まない）
APP_SCRIPT = "app.js"

# 描画のライブラリを入れる node_modules（リポジトリの直下で `npm ci` を済ませておく）
NODE_MODULES_DIR = REPO_ROOT / "node_modules"

# 配信元の URL（`/npm/{パッケージ}@{版}/{パス}`）から、パッケージ名とパスを取り出す
LIBRARY_URL_PATTERN = re.compile(r"/npm/(?P<package>[^@/]+)@[^/]+/(?P<path>.+)$")

# 描画のライブラリの読み込み結果（URL と本文）。テストをまたいで 1 回だけ読む
type LoadedLibrary = tuple[str, str]
_loaded_libraries: dict[str, LoadedLibrary] = {}

# mdmark の外部ライブラリの設計書の名前
MDMARK_DESIGN = "mdmark"

# mdmark の配布物を jsDelivr から取るとき、接続と 1 回の読み取りをそれぞれ待つ秒数
MDMARK_FETCH_TIMEOUT_SEC = 30

# 取った mdmark の配布物を置くフォルダ（node_modules の中。git の管理外。1 回取れば次からは取らない）
MDMARK_CACHE_DIR = NODE_MODULES_DIR / ".cache" / "mindstella-tests"


# mdmark の配布物の読み込み結果。テストをまたいで 1 回だけ読む
_mdmark_dists: list[MdmarkDist] = []
_mdmark_css_dists: list[MdmarkDist] = []

# mdmark の JavaScript の URL から CSS の URL を作る置き換え
MDMARK_JS_FILE = "index.js"
MDMARK_CSS_FILE = "index.css"


def _sha384_of(body: bytes) -> str:
    """中身の sha384 を `sha384-{Base64}` の形にして返す。"""
    return "sha384-" + base64.b64encode(hashlib.sha384(body).digest()).decode("ascii")


def _read_mdmark_dist() -> MdmarkDist:
    """外部ライブラリの設計書の mdmark の JavaScript を、integrity と突き合わせて返す。無ければ jsDelivr から取って置く。"""
    # 読み込み済みならそのまま返す
    if _mdmark_dists:
        return _mdmark_dists[0]
    design = yaml.safe_load((LIBRARY_DESIGN_DIR / f"{MDMARK_DESIGN}.yaml").read_text(encoding="utf-8"))
    url = design["version"]["source"]
    # 版の固定の仕方に書いてある最初の integrity が JavaScript の値（CSS の値はその後ろ）
    expected = re.search(r"sha384-[A-Za-z0-9+/=]+", design["version"]["pinning"])
    assert expected is not None, f"{MDMARK_DESIGN} の設計書に integrity がありません"
    cache_path = MDMARK_CACHE_DIR / f"{hashlib.sha256(expected.group(0).encode()).hexdigest()}.js"
    if cache_path.is_file():
        body = cache_path.read_bytes()
    else:
        # 設計書が固定した URL（jsDelivr の GitHub のタグ）から取る
        with urllib.request.urlopen(url, timeout=MDMARK_FETCH_TIMEOUT_SEC) as response:
            body = response.read()
    # 設計書が固定した中身と同じバイトか
    assert _sha384_of(body) == expected.group(0), f"{url} の中身が設計書の integrity と違います"
    if not cache_path.is_file():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(body)
    _mdmark_dists.append(
        MdmarkDist(url=url, integrity=expected.group(0), body=body.decode("utf-8"))
    )
    return _mdmark_dists[0]


def _read_mdmark_css_dist() -> MdmarkDist:
    """外部ライブラリの設計書の mdmark の CSS を、integrity と突き合わせて返す。無ければ jsDelivr から取って置く。"""
    # 読み込み済みならそのまま返す
    if _mdmark_css_dists:
        return _mdmark_css_dists[0]
    design = yaml.safe_load((LIBRARY_DESIGN_DIR / f"{MDMARK_DESIGN}.yaml").read_text(encoding="utf-8"))
    url = design["version"]["source"].replace(MDMARK_JS_FILE, MDMARK_CSS_FILE)
    # 版の固定の仕方に書いてある 2 つ目の integrity が CSS の値（最初は JavaScript の値）
    integrities = re.findall(r"sha384-[A-Za-z0-9+/=]+", design["version"]["pinning"])
    assert len(integrities) >= 2, f"{MDMARK_DESIGN} の設計書に CSS の integrity がありません"
    expected = integrities[1]
    cache_path = MDMARK_CACHE_DIR / f"{hashlib.sha256(expected.encode()).hexdigest()}.css"
    if cache_path.is_file():
        body = cache_path.read_bytes()
    else:
        # 設計書が固定した URL（jsDelivr の GitHub のタグ）から取る
        with urllib.request.urlopen(url, timeout=MDMARK_FETCH_TIMEOUT_SEC) as response:
            body = response.read()
    # 設計書が固定した中身と同じバイトか
    assert _sha384_of(body) == expected, f"{url} の中身が設計書の integrity と違います"
    if not cache_path.is_file():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(body)
    _mdmark_css_dists.append(MdmarkDist(url=url, integrity=expected, body=body.decode("utf-8")))
    return _mdmark_css_dists[0]


def _read_library(name: str) -> LoadedLibrary:
    """外部ライブラリの設計書の版と同じバイトを node_modules から読み、integrity と突き合わせて返す。"""
    # 読み込み済みならそのまま返す
    if name in _loaded_libraries:
        return _loaded_libraries[name]
    design = yaml.safe_load((LIBRARY_DESIGN_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    url = design["version"]["source"]
    expected = re.search(r"sha384-[A-Za-z0-9+/=]+", design["version"]["pinning"])
    assert expected is not None, f"{name} の設計書に integrity がありません"
    located = LIBRARY_URL_PATTERN.search(url)
    assert located is not None, f"{name} の設計書の URL が jsDelivr の形ではありません: {url}"
    # jsDelivr の `/npm/{名前}@{版}/{パス}` は、npm の同じ版の `{パス}` と同じバイト
    path = NODE_MODULES_DIR / located["package"] / located["path"]
    body = path.read_bytes()
    # 設計書が固定した版と同じバイトか
    digest = "sha384-" + base64.b64encode(hashlib.sha384(body).digest()).decode("ascii")
    assert digest == expected.group(0), f"{path} が設計書の integrity と違います"
    _loaded_libraries[name] = (url, body.decode("utf-8"))
    return _loaded_libraries[name]


@pytest.fixture
def preview_page(page: Page) -> Page:
    """空の文書を持つページを開いて返す。history.pushState が使える URL にする。"""
    page.route(
        PAGE_URL,
        lambda route: route.fulfill(
            body="<!doctype html><html><body></body></html>", content_type="text/html"
        ),
    )
    page.goto(PAGE_URL)
    return page


@pytest.fixture
def load_preview_scripts(preview_page: Page) -> LoadPreviewScripts:
    """tsc が生成した `.js` をページに読む関数を返す。"""

    def _load(*, include_app: bool = False) -> None:
        """プレビューの `.js` を、起動する `app.js` を除いて（include_app なら含めて）読む。"""
        paths = sorted(
            path
            for path in PREVIEW_DIR.rglob("*.js")
            if include_app or path.relative_to(PREVIEW_DIR).as_posix() != APP_SCRIPT
        )
        # tsc がまだ `.js` を生成していない
        if not paths:
            raise FileNotFoundError(f"tsc が生成した .js が {PREVIEW_DIR} にありません")
        for path in paths:
            preview_page.add_script_tag(path=str(path))

    return _load


@pytest.fixture
def load_library(preview_page: Page) -> LoadLibrary:
    """描画のライブラリを、配信元への要求に本文を返す形でページに読む関数を返す。"""

    def _load(name: str) -> None:
        """設計書の版のライブラリを `page.route` で返し、script 要素で読む。"""
        url, body = _read_library(name)
        preview_page.route(
            url, lambda route: route.fulfill(body=body, content_type="application/javascript")
        )
        preview_page.add_script_tag(url=url)

    return _load


@pytest.fixture
def mdmark_dist() -> MdmarkDist:
    """設計書が固定した mdmark の JavaScript の URL・integrity・中身を返す。"""
    return _read_mdmark_dist()


@pytest.fixture
def mdmark_css_dist() -> MdmarkDist:
    """設計書が固定した mdmark の CSS の URL・integrity・中身を返す。"""
    return _read_mdmark_css_dist()


@pytest.fixture
def serve_mdmark(preview_page: Page, mdmark_dist: MdmarkDist) -> ServeMdmark:
    """mdmark の JavaScript の URL への要求に答える関数を返す。"""

    def _serve(*, status: int = 200) -> None:
        """200 なら配布物の中身を、それ以外なら本文なしの応答を `page.route` で返す。"""
        if status == 200:
            preview_page.route(
                mdmark_dist.url,
                lambda route: route.fulfill(
                    body=mdmark_dist.body, content_type="text/javascript"
                ),
            )
        else:
            preview_page.route(
                mdmark_dist.url, lambda route: route.fulfill(status=status, body="")
            )

    return _serve


@pytest.fixture
def put_mdmark_import_map(preview_page: Page, mdmark_dist: MdmarkDist) -> PutMdmarkImportMap:
    """import map の `integrity` に mdmark の URL を書いた script をページに足す関数を返す。"""

    def _put(*, integrity: str | None = None) -> None:
        """設計書の値（`integrity` を渡せばその値）を、mdmark の URL の `integrity` にして足す。"""
        preview_page.evaluate(
            """({url, integrity}) => {
                const script = document.createElement("script");
                script.type = "importmap";
                script.textContent = JSON.stringify({integrity: {[url]: integrity}});
                document.head.append(script);
            }""",
            {
                "url": mdmark_dist.url,
                "integrity": mdmark_dist.integrity if integrity is None else integrity,
            },
        )

    return _put


@pytest.fixture
def put_embedded_mdmark(preview_page: Page, mdmark_dist: MdmarkDist) -> PutEmbeddedMdmark:
    """配る書き出しが mdmark の JavaScript を中身に持つ要素（`#mindmap-mdmark`）をページに足す関数を返す。"""

    def _put() -> None:
        """配布物の中身を持つ `script[type=text/plain]` を足す（import map は足さない）。"""
        preview_page.evaluate(
            """(body) => {
                const script = document.createElement("script");
                script.type = "text/plain";
                script.id = "mindmap-mdmark";
                script.textContent = body;
                document.body.append(script);
            }""",
            mdmark_dist.body,
        )

    return _put


@pytest.fixture
def put_mdmark_css(preview_page: Page, mdmark_css_dist: MdmarkDist) -> PutMdmarkCss:
    """mdmark の CSS の URL への要求に答え、その `link` をページに足す関数を返す。"""

    def _put(*, status: int = 200, tamper: bool = False) -> None:
        """200 なら配布物の中身（`tamper` なら `integrity` が合わなくなる中身）を、それ以外なら本文なしの応答を返し、設計書の `integrity` を持つ `link` を足す。"""
        if status == 200:
            body = mdmark_css_dist.body + "\n/* tampered */" if tamper else mdmark_css_dist.body
            preview_page.route(
                mdmark_css_dist.url,
                lambda route: route.fulfill(body=body, content_type="text/css"),
            )
        else:
            preview_page.route(
                mdmark_css_dist.url, lambda route: route.fulfill(status=status, body="")
            )
        preview_page.evaluate(
            """({url, integrity}) => {
                const link = document.createElement("link");
                link.rel = "stylesheet";
                link.href = url;
                link.integrity = integrity;
                link.crossOrigin = "anonymous";
                document.head.append(link);
            }""",
            {"url": mdmark_css_dist.url, "integrity": mdmark_css_dist.integrity},
        )

    return _put


@pytest.fixture
def load_mdmark(
    preview_page: Page, serve_mdmark: ServeMdmark, put_mdmark_import_map: PutMdmarkImportMap
) -> LoadMdmark:
    """mdmark をページに読んでグローバルに置く関数を返す（`load_preview_scripts` の後に呼ぶ）。"""

    def _load() -> None:
        """配信元と import map を用意して、`loadMdmark` で読む。"""
        serve_mdmark()
        put_mdmark_import_map()
        preview_page.evaluate("() => MindmapPreview.loadMdmark()")

    return _load


@pytest.fixture
def load_preview_styles(preview_page: Page) -> LoadPreviewStyles:
    """プレビューの CSS（tokens.css・style.css）をページに読む関数を返す。"""

    def _load() -> None:
        """位置・大きさ・表示を CSS が決める部品を調べるテストで、画面と同じ CSS を当てる。"""
        for name in STYLE_FILES:
            preview_page.add_style_tag(path=str(PREVIEW_DIR / name))

    return _load


@pytest.fixture
def make_data(valid_settings: dict[str, Any]) -> MakeData:
    """埋め込みのデータ（`mindmap-data` の中身）を作る関数を返す。"""

    def _make(
        *, settings: dict[str, Any] | None = None, next_ids: list[str] | None = None, **kinds: Any
    ) -> dict[str, Any]:
        """種類ごとの項目（decisions=[...] など）と、次の候補の ID を渡して埋め込みのデータを返す。"""
        data: dict[str, Any] = {
            "settings": valid_settings if settings is None else settings,
            "decisions": [],
            "tasks": [],
            "research": [],
            "docs": [],
            "terms": [],
            "notes": [],
            "logs": [],
            "bodies": {},
            "derived": {
                "next": [
                    {
                        "id": item_id,
                        "title": f"{item_id}の題",
                        "phase": None,
                        "weight": None,
                        "followers": 0,
                    }
                    for item_id in (next_ids or [])
                ],
                "goal": {
                    "reached": False,
                    "goal_phase": "構成",
                    "phases": [],
                    "remaining_decisions": [],
                    "remaining_deliverables": [],
                    "phase_progress": [],
                },
                "progress": [],
            },
            "built_at": "2026-10-02T08:00:00+00:00",
        }
        data.update(kinds)
        return data

    return _make
