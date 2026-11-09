// テスト用のマイクと録音: getUserMedia と MediaRecorder を差し替え、止めたトラックの数を数える
import { vi } from "vitest";

export type FakeMedia = {
  /** 止めたトラックの数 */
  readonly stoppedTracks: () => number;
};

/** getUserMedia と MediaRecorder を差し替える。failure を渡すと getUserMedia がその名前の DOMException で断る */
export const installFakeMedia = (failure?: string): FakeMedia => {
  let stopped = 0;
  const track = { stop: () => (stopped += 1) };
  class FakeRecorder {
    static isTypeSupported(type: string): boolean {
      return type === "audio/webm;codecs=opus";
    }
    readonly mimeType: string;
    private readonly listeners: Record<string, (event: { data?: Blob }) => void> = {};
    constructor(_stream: unknown, options?: { mimeType?: string }) {
      this.mimeType = options?.mimeType ?? "";
    }
    addEventListener(name: string, listener: (event: { data?: Blob }) => void): void {
      this.listeners[name] = listener;
    }
    start(): void {}
    stop(): void {
      this.listeners.dataavailable?.({ data: new Blob(["ab"]) });
      this.listeners.stop?.({});
    }
  }
  vi.stubGlobal("MediaRecorder", FakeRecorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: async () => {
        if (failure !== undefined) throw new DOMException("x", failure);
        return { getTracks: () => [track] };
      },
    },
  });
  return { stoppedTracks: () => stopped };
};

/** マイクを使えないページにする（mediaDevices を外す） */
export const removeFakeMedia = (): void => {
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
  vi.unstubAllGlobals();
};
