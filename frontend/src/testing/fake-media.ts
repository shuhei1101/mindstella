// テスト用のマイクと録音: getUserMedia・MediaRecorder・AudioContext を差し替え、止めたトラックと閉じた音声の処理の数を数える
import { vi } from "vitest";

export type FakeMedia = {
  /** 止めたトラックの数 */
  readonly stoppedTracks: () => number;
  /** close した AudioContext の数 */
  readonly closedContexts: () => number;
};

/**
 * getUserMedia・MediaRecorder・AudioContext を差し替える。
 * failure を渡すと getUserMedia がその名前の DOMException で断る。
 * peaks は音量を取るたびに順に返す波形の最大の値（128 が無音、255 が最大。無ければ 192）
 */
export const installFakeMedia = (failure?: string, peaks: readonly number[] = [192]): FakeMedia => {
  let stopped = 0;
  let closed = 0;
  let read = 0;
  class FakeAudioContext {
    createMediaStreamSource(): { connect: () => void } {
      return { connect: () => {} };
    }
    createAnalyser(): { fftSize: number; getByteTimeDomainData: (values: Uint8Array) => void } {
      return {
        fftSize: 2048,
        getByteTimeDomainData: (values: Uint8Array) => {
          values.fill(128);
          values[0] = peaks[Math.min(read, peaks.length - 1)] ?? 128;
          read += 1;
        },
      };
    }
    close(): Promise<void> {
      closed += 1;
      return Promise.resolve();
    }
  }
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
  vi.stubGlobal("AudioContext", FakeAudioContext);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: () => {
        if (failure !== undefined) return Promise.reject(new DOMException("x", failure));
        return Promise.resolve({ getTracks: () => [track] });
      },
    },
  });
  return { stoppedTracks: () => stopped, closedContexts: () => closed };
};

/** マイクを使えないページにする（mediaDevices を外す） */
export const removeFakeMedia = (): void => {
  Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
  vi.unstubAllGlobals();
};
