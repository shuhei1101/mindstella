// テスト用の画面の消灯の抑止: navigator.wakeLock を差し替え、求めた回数と解いた回数を数える

export type FakeWakeLock = {
  /** request に渡った種類の並び */
  readonly requested: () => string[];
  /** release を呼んだ回数 */
  readonly released: () => number;
};

/** navigator.wakeLock を差し替える。mode が denied なら request が NotAllowedError で断り、missing なら navigator.wakeLock を持たない */
export const installFakeWakeLock = (mode: "ok" | "denied" | "missing" = "ok"): FakeWakeLock => {
  const requested: string[] = [];
  let released = 0;
  const value =
    mode === "missing"
      ? undefined
      : {
          request: (type: string) => {
            requested.push(type);
            if (mode === "denied") return Promise.reject(new DOMException("x", "NotAllowedError"));
            return Promise.resolve({
              released: false,
              release: () => {
                released += 1;
                return Promise.resolve();
              },
            });
          },
        };
  Object.defineProperty(navigator, "wakeLock", { configurable: true, value });
  return { requested: () => [...requested], released: () => released };
};

/** navigator.wakeLock を外す */
export const removeFakeWakeLock = (): void => {
  Object.defineProperty(navigator, "wakeLock", { configurable: true, value: undefined });
};
