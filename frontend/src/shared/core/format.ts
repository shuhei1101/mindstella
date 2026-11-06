// 画面に出す値の整形

/** UTC のタイムゾーン付き ISO 8601 を JST の `MM/DD HH:mm` にする */
export const formatJst = (iso: string): string => {
  const parts = new Intl.DateTimeFormat("ja-JP", { timeZone: "Asia/Tokyo", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(iso));
  const part = (type: Intl.DateTimeFormatPartTypes): string => parts.find((entry) => entry.type === type)?.value ?? "";
  return `${part("month")}/${part("day")} ${part("hour")}:${part("minute")}`;
};

/** 値が無いときに出す文字 */
export const NO_VALUE = "（なし）";

/** 押した位置からこの距離（px）までの動きは、押しただけとして扱う */
export const PRESS_SLOP_PX = 5;

/** 値を文字にする（オブジェクトは JSON の文字にする） */
export const toText = (value: unknown): string => (typeof value === "object" ? JSON.stringify(value) : `${value as string | number | boolean}`);
