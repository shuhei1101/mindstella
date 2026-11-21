import { afterEach, describe, expect, test } from "vitest";

import { embeddedResponse, isEmbedded, readEmbeddedData, resetEmbeddedDataForTest } from "@/shared/core/embedded";

/** 記録の mindmap-data の要素を body に置く */
const placeData = (text: string) => {
  const element = document.createElement("script");
  element.type = "application/json";
  element.id = "mindmap-data";
  element.textContent = text;
  document.body.append(element);
};

afterEach(() => {
  document.body.replaceChildren();
  resetEmbeddedDataForTest();
});

describe("readEmbeddedData", () => {
  // 要素の中身の JSON を返す（正常系）
  test("read_embedded_data", () => {
    // 準備
    placeData('{"settings":{}}');
    // 実行
    const result = readEmbeddedData();
    // 検証
    expect(result).toEqual({ settings: {} });
  });

  // 要素が無いか空なら null（正常系）
  test.each([
    ["missing", null],
    ["blank", "  \n "],
  ])("read_embedded_data_when_missing %s", (_name, text) => {
    // 準備
    if (text !== null) placeData(text);
    // 実行
    const result = readEmbeddedData();
    // 検証
    expect(result).toBeNull();
  });
});

describe("isEmbedded", () => {
  // 埋め込みの記録の有無で分かれる（正常系）
  test.each([
    ["present", '{"settings":{}}', true],
    ["absent", null, false],
  ])("is_embedded %s", (_name, text, expected) => {
    // 準備
    if (text !== null) placeData(text);
    // 実行
    const result = isEmbedded();
    // 検証
    expect(result).toBe(expected);
  });
});

describe("embeddedResponse", () => {
  // 記録と空の応答を返す（正常系）
  test("embedded_response", () => {
    // 準備
    placeData('{"settings":{"summary":"家計簿"}}');
    // 実行
    const records = embeddedResponse({ url: "/api/records", method: "GET" });
    const threads = embeddedResponse({ url: "/api/threads?x=1", method: "GET" });
    // 検証
    expect(records?.data).toEqual({ settings: { summary: "家計簿" } });
    expect(records?.status).toBe(200);
    expect(threads?.data).toEqual({ threads: [] });
  });

  // 書き込みとほかのパスは null（正常系）
  test.each([
    ["POST", "/api/comments"],
    ["GET", "/api/transcription"],
  ])("embedded_response_when_not_supported %s %s", (method, url) => {
    // 準備
    placeData('{"settings":{}}');
    // 実行
    const result = embeddedResponse({ url, method });
    // 検証
    expect(result).toBeNull();
  });
});
