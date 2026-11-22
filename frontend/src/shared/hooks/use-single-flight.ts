// 書き込みの操作を、前の操作の応答と再読み込みが終わるまで同期に止め、要求を 1 件ずつにする（モジュール構成『use-single-flight』）
import { useCallback, useRef, useState } from "react";

/** `run(task)` と、動いているか。前の `task` が終わる前の `run` は `task` を呼ばずに戻る */
export const useSingleFlight = () => {
  // 再描画を待たずに 2 回目を止めるため、フラグは ref で持つ
  const flying = useRef(false);
  const [running, setRunning] = useState(false);
  const run = useCallback((task: () => Promise<unknown>): void => {
    if (flying.current) return;
    flying.current = true;
    setRunning(true);
    // 拒否は呼び出し側の onError が扱うため、ここでは捨てる
    void task()
      .catch(() => undefined)
      .finally(() => {
        flying.current = false;
        setRunning(false);
      });
  }, []);
  return { run, running };
};
