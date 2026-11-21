// 一覧（表・ボード・カード）のスクロール領域の位置を残し、画面へ戻ったときに描画の後に戻す
import { useCallback, useEffect, useRef, type RefCallback } from "react";

import { readListScroll, writeListScroll } from "@/shared/stores/screen-state-store";

/** `key`（`{画面}:{表示形式}`）のスクロール位置を残し、行を描き終えたら 1 度だけ戻す ref を返却する */
export const useListScroll = (key: string, ready: boolean): RefCallback<HTMLElement> => {
  const element = useRef<HTMLElement | null>(null);
  // 最新の key と ready（ref と scroll の処理から参照する）
  const latest = useRef({ key, ready });
  // 位置を戻し終えた key
  const restored = useRef<string | null>(null);
  // スクロールの書き込みを待っているか
  const pending = useRef(false);

  const restore = useCallback((): void => {
    const target = element.current;
    const { key: current, ready: drawn } = latest.current;
    // 要素が無い・行を描き終えていない・戻し終えた key: 戻さない
    if (target === null || !drawn || restored.current === current) return;
    restored.current = current;
    const position = readListScroll(current);
    if (position === null) return;
    requestAnimationFrame(() => {
      target.scrollTop = position.top;
      target.scrollLeft = position.left;
    });
  }, []);

  const onScroll = useCallback((): void => {
    if (pending.current) return;
    pending.current = true;
    requestAnimationFrame(() => {
      pending.current = false;
      const target = element.current;
      if (target === null) return;
      writeListScroll(latest.current.key, { top: target.scrollTop, left: target.scrollLeft });
    });
  }, []);

  // スクロール領域（ブラウザの DOM）と key・行の描画を同期する
  useEffect(() => {
    latest.current = { key, ready };
    restore();
  }, [key, ready, restore]);

  return useCallback(
    (node: HTMLElement | null): void => {
      element.current?.removeEventListener("scroll", onScroll);
      element.current = node;
      if (node === null) return;
      node.addEventListener("scroll", onScroll, { passive: true });
      restore();
    },
    [onScroll, restore],
  );
};
