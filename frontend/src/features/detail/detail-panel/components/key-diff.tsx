// 変わったキーの前の値と今の値を並べる。文字どうしは変わった語に面を付ける
import type { ReactNode } from "react";

import { useLibrary } from "@/shared/adapters/libraries";
import { diffInline, LINE_DIFF_TIMEOUT_MS, type InlinePart, type JsDiff } from "@/shared/core/diff";
import { NO_VALUE } from "@/shared/core/format";
import type { Item } from "@/shared/core/records";

/** 差分に出さないキー */
const UNDIFFED_KEYS = new Set(["id", "created", "updated", "updated_by", "history", "history_dropped_seq", "body"]);

/** キーの値を差分に並べる文字にする。値が無ければ null */
export const valueText = (value: unknown): string | null => {
  if (value === undefined || value === null || value === "") return null;
  if (Array.isArray(value)) return value.length === 0 ? null : value.join("、");
  return String(value as string | number | boolean);
};

/** 前の版と後の版で値が変わったキーの見分けと、前の版 */
export type KeyDiffs = { has: (key: string) => boolean; left: Record<string, unknown>; right: Record<string, unknown> };

export const keyDiffs = (before: Item, after: Item): KeyDiffs => {
  const left: Record<string, unknown> = { ...before };
  const right: Record<string, unknown> = { ...after };
  const changed = new Set([...new Set([...Object.keys(left), ...Object.keys(right)])].filter((key) => !UNDIFFED_KEYS.has(key) && JSON.stringify(left[key]) !== JSON.stringify(right[key])));
  return { has: (key) => changed.has(key), left, right };
};

const Words = ({ parts }: { parts: InlinePart[] }) => (
  <>
    {parts.map((part, position) =>
      part.kind === "same" ? (
        part.text
      ) : (
        // 部分の並びは変わらない
        // eslint-disable-next-line @eslint-react/no-array-index-key
        <span key={position} className={`df-word df-${part.kind === "added" ? "add" : "del"}`}>
          {part.text}
        </span>
      ),
    )}
  </>
);

export type KeyDiffProps = { was: ReactNode; now: ReactNode; plain?: boolean };

export const KeyDiff = ({ was, now, plain = false }: KeyDiffProps) => {
  const { library } = useLibrary("jsdiff");
  const empty = (value: ReactNode): boolean => value === null || value === undefined || value === false || value === "";
  const inline = typeof was === "string" && typeof now === "string" && was !== "" && now !== "" && library !== null ? diffInline(was, now, performance.now() + LINE_DIFF_TIMEOUT_MS, library as JsDiff) : null;
  return (
    <span className={plain ? "df-kv df-plain" : "df-kv"}>
      <del className="df-was">
        <span className="sr-only">前の値: </span>
        {inline === null ? (empty(was) ? NO_VALUE : was) : <Words parts={inline.before} />}
      </del>
      <span className="df-arrow" aria-hidden="true">
        →
      </span>
      <ins className="df-now">
        <span className="sr-only">今の値: </span>
        {inline === null ? (empty(now) ? NO_VALUE : now) : <Words parts={inline.after} />}
      </ins>
    </span>
  );
};
