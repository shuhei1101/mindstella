import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { HtmlBodyFrame } from "@/shared/components/html-body-frame";

describe("HtmlBodyFrame", () => {
  // スクリプトを動かさない枠（正常系）
  test("html_body_frame", () => {
    // 実行
    render(<HtmlBodyFrame source="<p>本文</p>" label="本文" />);
    // 検証
    expect(screen.getByTitle("本文")).toHaveAttribute("sandbox", "allow-same-origin");
  });
});
