// 書き込みの操作を、前の操作の応答と再読み込みが終わるまで同期に止め、要求を 1 件ずつにする（モジュール構成『use-single-flight』）
import { useCallback, useRef, useState } from "react";
import { flushSync } from "react-dom";

/** `run(task, after)` と、動いているか。前の `task` が終わる前の `run` は `task` を呼ばずに戻る。`after` は押せる状態を描いた後に呼ぶ */
export const useSingleFlight = () => {
  // 再描画を待たずに 2 回目を止めるため、フラグは ref で持つ
  const flying = useRef(false);
  const [running, setRunning] = useState(false);
  const run = useCallback((task: () => Promise<unknown>, after?: () => void): void => {
    if (flying.current) return;
    flying.current = true;
    setRunning(true);
    // 拒否は呼び出し側の onError が扱うため、ここでは捨てる
    void task()
      .catch(() => undefined)
      .finally(() => {
        flying.current = false;
        // 押せる状態を描き終えてから after を呼ぶ（running で押せなくしていたボタンへフォーカスを移せるように）
        flushSync(() => { setRunning(false); });
        after?.();
      });
  }, []);
  return { run, running };
};
