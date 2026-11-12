// jsdom のキャンバスは描かないため、2D の文脈の呼び出しと値の書き換えを記録する差し替え

/** 記録した 1 件（メソッドの呼び出しか、値の書き換え） */
export type CanvasCall = { name: string; args: unknown[] };

/** 呼び出しを記録する 2D の文脈と、その記録 */
export type RecordingContext = { context: CanvasRenderingContext2D; calls: CanvasCall[] };

/** グラデーション・パターンの代わり（色の追加も記録する） */
const fakeGradient = (calls: CanvasCall[]) => ({
  addColorStop: (...args: unknown[]) => {
    calls.push({ name: "addColorStop", args });
  },
});

/** 呼び出しを記録する 2D の文脈を作る */
export const createRecordingContext = (canvas?: HTMLCanvasElement): RecordingContext => {
  const calls: CanvasCall[] = [];
  const values: Record<string, unknown> = {
    canvas: canvas ?? document.createElement("canvas"),
    globalAlpha: 1,
    globalCompositeOperation: "source-over",
    lineWidth: 1,
    fillStyle: "#000000",
    strokeStyle: "#000000",
    font: "10px sans-serif",
  };
  const context = new Proxy(values, {
    get: (target, key: string) => {
      if (key in target) return target[key];
      if (key === "createRadialGradient" || key === "createLinearGradient" || key === "createConicGradient" || key === "createPattern") {
        return (...args: unknown[]) => {
          calls.push({ name: key, args });
          return fakeGradient(calls);
        };
      }
      if (key === "measureText") return (text: string) => ({ width: text.length * 6, actualBoundingBoxAscent: 8, actualBoundingBoxDescent: 2 });
      if (key === "getLineDash") return () => [];
      if (key === "getTransform") return () => new DOMMatrix();
      return (...args: unknown[]) => {
        calls.push({ name: key, args });
      };
    },
    set: (target, key: string, value: unknown) => {
      target[key] = value;
      calls.push({ name: `set:${key}`, args: [value] });
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { context, calls };
};
