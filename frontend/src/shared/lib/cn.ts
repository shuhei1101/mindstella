// クラス名を合わせる（後のクラスで前の同じ種類のクラスを上書きする）
import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/** index.css の @theme inline で足した文字の大きさと角丸（色のクラスと取り違えないよう教える） */
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: ["body", "small", "h2", "num", "count", "tab-count", "rank", "next", "next-narrow", "hero", "hero-narrow", "goal", "goal-sub"],
      radius: ["control", "kbd"],
    },
  },
});

export const cn = (...inputs: ClassValue[]): string => twMerge(clsx(inputs));
