import { fireEvent, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { stubRecords } from "@/testing/msw/fixtures";
import { DetailHeader, type DetailHeaderProps } from "@/features/detail/detail-panel/components/detail-header";
import { buildIndex, type MindmapData } from "@/shared/core/records";
import { sampleRecordLookup } from "@/testing/record-lookup";
import { renderInPreviewRouter, renderRoute } from "@/testing/render";

vi.mock("@/shared/adapters/libraries", async (original) => ({ ...(await original<object>()), ...(await import("@/testing/libraries")) }));

const DATA = { decisions: [{ id: "D-2", title: "保存先を決める", status: "未決定" }], tasks: [], research: [], docs: [], terms: [], notes: [], logs: [], derived: { ready: [] }, settings: {}, bodies: {} } as unknown as MindmapData;

const props = (patch: Partial<DetailHeaderProps> = {}): DetailHeaderProps => ({
  item: DATA.decisions[0] as DetailHeaderProps["item"],
  kind: "decisions",
  index: buildIndex(DATA),
  full: false,
  editable: false,
  editing: false,
  comments: false,
  pending: null,
  showTitle: false,
  lookup: sampleRecordLookup,
  onOpenRecord: vi.fn(),
  onToggleEdit: vi.fn(),
  onToggleFull: vi.fn(),
  onClose: vi.fn(),
  ...patch,
});

describe("DetailHeader", () => {
  // 見出しがあるときだけ目次のボタンを描く（正常系）
  test.each([
    { body: "# 目的\n\n本文\n\n## 保存先", expected: true },
    { body: "見出しの無い本文", expected: false },
  ])("detail_header_when_toc", async ({ body, expected }) => {
    // 準備
    stubRecords({ docs: [{ id: "A-1", title: "目次の資料の題", status: "確認中", body: "docs/A-1.md", created: "2026-11-01T00:00:00+00:00", updated: "2026-11-01T00:00:00+00:00" }], bodies: { "docs/A-1.md": body } });
    // 実行
    renderRoute("/?tab=docs&id=A-1");
    const panel = await screen.findByRole("complementary", { name: /詳細/ });
    await within(panel).findAllByText("目次の資料の題");
    // 検証
    const button = within(panel).queryByRole("button", { name: "本文の目次" });
    if (expected) expect(button).toBeInTheDocument();
    else expect(button).toBeNull();
  });

  // 一覧の並びの前後を戻る・進むの左に描く（正常系）
  test.each([
    { sibling: { position: 2, total: 3, onPrev: vi.fn(), onNext: vi.fn() }, expected: true },
    { sibling: null, expected: false },
  ])("detail_header_when_sibling (expected: $expected)", async ({ sibling, expected }) => {
    // 実行
    await renderInPreviewRouter("/?tab=decisions&id=D-2", <DetailHeader {...props({ sibling })} />);
    // 検証
    const back = await screen.findByRole("button", { name: "前の項目へ戻る" });
    const position = screen.queryByText("2 / 3");
    if (expected) {
      expect(position).toBeInTheDocument();
      expect(position?.compareDocumentPosition(back)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    } else {
      expect(position).toBeNull();
    }
  });

  // j・k で前後へ移る（正常系）
  test.each([
    { name: "j", init: { key: "j", code: "KeyJ" }, expected: "next" },
    { name: "k", init: { key: "k", code: "KeyK" }, expected: "prev" },
    { name: "入力欄の j", init: { key: "j", code: "KeyJ" }, inInput: true, expected: null },
    { name: "Ctrl+j", init: { key: "j", code: "KeyJ", ctrlKey: true }, expected: null },
    { name: "isComposing の j", init: { key: "j", code: "KeyJ", isComposing: true }, expected: null },
  ])("detail_header_when_key: $name", async ({ init, inInput = false, expected }) => {
    // 準備
    const onPrev = vi.fn();
    const onNext = vi.fn();
    await renderInPreviewRouter(
      "/?tab=decisions&id=D-2",
      <>
        <DetailHeader {...props({ sibling: { position: 2, total: 3, onPrev, onNext } })} />
        <input aria-label="入力欄" />
      </>,
    );
    await screen.findByText("2 / 3");
    const input = screen.getByRole("textbox", { name: "入力欄" });
    if (inInput) input.focus();
    // 実行
    fireEvent.keyDown(inInput ? input : document.body, { bubbles: true, cancelable: true, ...init });
    // 検証
    expect(onNext).toHaveBeenCalledTimes(expected === "next" ? 1 : 0);
    expect(onPrev).toHaveBeenCalledTimes(expected === "prev" ? 1 : 0);
  });
});
