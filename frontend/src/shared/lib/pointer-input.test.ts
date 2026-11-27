import { beforeEach, describe, expect, test, vi } from "vitest";

type Step = { type: "pointerdown" | "pointerover"; pointerType: string } | { type: "keydown" };

/** 文書へ入力のイベントを順に送信する（jsdom は PointerEvent を持たないため、pointerType を持つ Event を作る） */
const send = (steps: Step[]): void => {
  for (const step of steps) {
    const event = new Event(step.type, { bubbles: true });
    if (step.type !== "keydown") Object.defineProperty(event, "pointerType", { value: step.pointerType });
    document.body.dispatchEvent(event);
  }
};

describe("isTouchInput", () => {
  beforeEach(() => {
    // 直前の入力はモジュールが持つため、ケースごとに再読み込みする
    vi.resetModules();
  });

  // 直前の入力で判定する（正常系）
  test.each([
    { name: "何も送信しない", steps: [] as Step[], expected: false },
    { name: "touch の pointerdown", steps: [{ type: "pointerdown", pointerType: "touch" }] as Step[], expected: true },
    { name: "mouse の pointerdown", steps: [{ type: "pointerdown", pointerType: "mouse" }] as Step[], expected: false },
    { name: "touch の pointerdown の後に keydown", steps: [{ type: "pointerdown", pointerType: "touch" }, { type: "keydown" }] as Step[], expected: false },
    { name: "touch の pointerdown の後に mouse の pointerover", steps: [{ type: "pointerdown", pointerType: "touch" }, { type: "pointerover", pointerType: "mouse" }] as Step[], expected: false },
  ])("is_touch_input（$name）", async ({ steps, expected }) => {
    // 準備
    const { isTouchInput } = await import("@/shared/lib/pointer-input");
    // 実行
    send(steps);
    // 検証
    expect(isTouchInput()).toBe(expected);
  });
});
