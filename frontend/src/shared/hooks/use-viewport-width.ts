// 表示の幅を返却し、窓の幅が変わったら描き直させるフック（左のパネルと詳細パネルが上限を求めるのに使用する）
import { useSyncExternalStore } from "react";

import { LEFT_PANEL_WIDTH } from "@/shared/stores/panel-width-store";

/** 幅の区切りを出す表示の幅の media query */
const RESIZABLE_QUERY = `(min-width: ${LEFT_PANEL_WIDTH.resizableFrom}px)`;

/** 表示の幅が変わったら描き直す（resize と、区切りを出す幅をまたいだ matchMedia の変化） */
const subscribeViewport = (onChange: () => void): (() => void) => {
  window.addEventListener("resize", onChange);
  const media = typeof window.matchMedia === "function" ? window.matchMedia(RESIZABLE_QUERY) : null;
  media?.addEventListener("change", onChange);
  return () => {
    window.removeEventListener("resize", onChange);
    media?.removeEventListener("change", onChange);
  };
};

const viewportWidth = (): number => window.innerWidth;

export const useViewportWidth = (): number => useSyncExternalStore(subscribeViewport, viewportWidth);
