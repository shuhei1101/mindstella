import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { DetailResizer } from "@/features/detail/detail-panel/components/detail-resizer";

beforeEach(() => {
  // jsdom はポインターの捕捉を持たないため、捕捉の呼び出しだけを受ける
  HTMLElement.prototype.setPointerCapture = vi.fn();
  HTMLElement.prototype.releasePointerCapture = vi.fn();
  // 本文を寄せる幅（上限は表示の幅 − 400）
  window.innerWidth = 1400;
});

const Harness = () => {
  const [width, setWidth] = useState(640);
  return <DetailResizer width={width} onChange={setWidth} />;
};

describe("DetailResizer", () => {
  // 指のドラッグで幅を変える（正常系）
  test("detail_resizer_when_touch", () => {
    // 準備
    render(<Harness />);
    const separator = screen.getByRole("separator", { name: "詳細パネルの幅" });
    // 実行
    fireEvent.pointerDown(separator, { pointerType: "touch", pointerId: 1, clientX: 700 });
    fireEvent.pointerMove(separator, { pointerType: "touch", pointerId: 1, clientX: 600 });
    fireEvent.pointerUp(separator, { pointerType: "touch", pointerId: 1, clientX: 600 });
    // 検証（左へ 100px 動かした分だけ広がる）
    expect(separator).toHaveAttribute("aria-valuenow", "740");
  });
});
