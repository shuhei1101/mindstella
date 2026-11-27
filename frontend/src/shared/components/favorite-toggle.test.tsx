import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FavoriteToggle } from "@/shared/components/favorite-toggle";

describe("FavoriteToggle", () => {
  // 押すと onToggle だけを呼ぶ（正常系）
  test.each([false, true])("favorite_toggle on=%s", async (on) => {
    // 準備
    const onToggle = vi.fn();
    const onParent = vi.fn();
    render(
      // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions -- 親へ伝わらないことを確かめる
      <div onClick={onParent}>
        <FavoriteToggle title="題" on={on} onToggle={onToggle} />
      </div>,
    );
    const button = screen.getByRole("button", { name: "題をお気に入りに登録" });
    // 実行
    await userEvent.click(button);
    // 検証
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(onParent).not.toHaveBeenCalled();
    expect(button).toHaveAttribute("aria-pressed", String(on));
  });
});
