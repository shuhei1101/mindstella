"""部品設計『消した項目の帯』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 帯の項目を読む（ID・タイトル・縦の位置・タイトルの行の数・途中で切れているか・省略記号の指定）
ITEMS_SCRIPT = """() => [...document.querySelectorAll('.rm-band .rm-item')].map(item => ({
    id: item.dataset.removedId,
    title: item.querySelector('.rm-ttl').textContent,
    top: item.getBoundingClientRect().top,
    lines: Math.round(item.querySelector('.rm-ttl').getBoundingClientRect().height
        / parseFloat(getComputedStyle(item.querySelector('.rm-ttl')).lineHeight)),
    clipped: item.querySelector('.rm-ttl').scrollWidth > item.querySelector('.rm-ttl').clientWidth,
    overflow: getComputedStyle(item.querySelector('.rm-ttl')).textOverflow,
}))"""

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 長いタイトルが折り返す幅
WRAP_SIZE = {"width": 640, "height": 600}


def test_one(open_story: OpenStory) -> None:
    """1 件。見出し「消した項目」と件数 1 の右に、消した印・ID・タイトルを 1 つ並べる（正常系）。"""
    # 準備・実行
    page = open_story("preview-removedband--one")
    # 検証
    band = page.locator("section.rm-band")
    assert band.get_attribute("aria-label") == "この時点で消した項目"
    heading = band.locator("h2.rm-band-t")
    assert heading.inner_text().split("\n")[0] == "消した項目"
    assert heading.locator(".n").inner_text() == "1"
    item = band.locator("ul.rm-list > li.rm-item")
    assert item.count() == 1
    assert item.locator(".df-mark.df-del").get_attribute("title") == "消した"
    assert item.locator(".mono").inner_text() == "N-6"
    assert item.locator(".rm-ttl").inner_text() == "ゴールを後から変える・足す・無しで始める"
    # 項目は押せる要素にしない
    assert band.locator("button, a, [tabindex]").count() == 0
    # 見出しの右に項目を並べる
    heading_box = heading.bounding_box()
    item_box = item.bounding_box()
    assert heading_box is not None
    assert item_box is not None
    assert heading_box["x"] + heading_box["width"] <= item_box["x"]
    assert item_box["y"] < heading_box["y"] + heading_box["height"]


def test_many_long_titles(open_story: OpenStory) -> None:
    """3 件で長いタイトルを含む。項目を横に並べ、狭めると項目ごと折り返し、タイトルは途中で切らずに折り返す（正常系）。"""
    # 準備
    page = open_story("preview-removedband--many-long-titles")
    # 検証（広い幅: 項目を同じ行に横に並べる）
    items = page.evaluate(ITEMS_SCRIPT)
    assert [item["id"] for item in items] == ["D-53", "D-54", "D-55"]
    assert len({item["top"] for item in items}) == 1
    assert page.locator(".rm-band-t .n").inner_text() == "3"
    # 実行（幅を狭める）
    page.set_viewport_size(WRAP_SIZE)
    page.wait_for_function("innerWidth === 640")
    # 検証（狭い幅: 項目が次の行へ折り返し、長いタイトルは複数行になる）
    wrapped = page.evaluate(ITEMS_SCRIPT)
    assert len({item["top"] for item in wrapped}) > 1
    long_title = wrapped[1]
    assert long_title["title"] == "変更履歴のモーダルを時系列の一覧にして、未読の印を付け、読んだ時点から後の書き換えだけを数えるか"
    assert long_title["lines"] >= 2
    # 途中で切らない（省略記号も隠しもしない）
    assert all(item["clipped"] is False and item["overflow"] == "clip" for item in wrapped)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px。見出しの下に項目を折り返し、画面幅の中に収める（正常系）。"""
    # 準備
    page = open_story("preview-removedband--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行
    heading_box = page.locator(".rm-band-t").bounding_box()
    list_box = page.locator(".rm-list").bounding_box()
    band_box = page.locator(".rm-band").bounding_box()
    # 検証
    assert heading_box is not None
    assert list_box is not None
    assert band_box is not None
    assert list_box["y"] >= heading_box["y"] + heading_box["height"]
    assert band_box["x"] >= 0
    assert band_box["x"] + band_box["width"] <= 390
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert [item["id"] for item in page.evaluate(ITEMS_SCRIPT)] == ["N-6", "N-7"]
