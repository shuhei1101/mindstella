// 記録の文字を描き、記録にある項目の ID・スレッドの ID を、押せない場所ではリンク、押す要素の中ではマーカーにする部品
import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { TermTip } from "@/shared/components/term-tip";
import { hashWith } from "@/shared/core/body-links";
import { findRecordIds, type LookupRecordId, type RecordIdTarget } from "@/shared/core/record-ids";
import { KIND_KEYS, KIND_LABEL, type Item } from "@/shared/core/records";
import type { TermTipEntry } from "@/shared/core/term-tips";

/** `link` は押せない場所、`marker` は押す要素の中（カード・行・検索の結果） */
export type RecordTextMode = "link" | "marker";

export type RecordTextProps = {
  text: string;
  mode: RecordTextMode;
  lookup: LookupRecordId;
  /** `link` の ID を押したとき */
  onOpen?: (id: string) => void;
  /** `marker` のとき、行の中の ID の説明を描く要素の id。使用する側が行のボタンの `aria-describedby` に指定する */
  descriptionId?: string;
};

/** 押す要素の中のマーカーのフォーカスを受ける祖先（行のボタン・検索の結果の `option`・リンク） */
const MARKER_HOST = "button, [role='option'], a";

/** 読み上げの説明の文（タイトル・ID・種類・状態） */
const describeTarget = (target: RecordIdTarget): string => [`${target.title}（${target.id}）`, target.kindLabel, target.status].filter((value) => value !== undefined).join(" ");

/** スレッドの状態の名前から状態を戻す */
const THREAD_STATUS_OF: Readonly<Record<string, "open" | "closed">> = { オープン: "open", クローズ: "closed" };

/** ID の中身を、部品『本文のマーカーのツールチップ』の種類 `item`・`thread` の 1 件にする（種類の名前が記録の種類に無いときは出さない） */
const tipEntryOf = (target: RecordIdTarget): TermTipEntry | null => {
  if (target.kind === "thread") return { kind: "thread", id: target.id, title: target.title, status: target.status === undefined ? undefined : THREAD_STATUS_OF[target.status] };
  const itemKind = KIND_KEYS.find((kind) => KIND_LABEL[kind] === target.kindLabel);
  if (itemKind === undefined) return null;
  const item: Item = { id: target.id, title: target.title, created: "", updated: "", ...(target.status === undefined ? {} : { status: target.status }) };
  return { kind: "item", itemKind, item };
};

type ShownTip = { anchor: HTMLElement; entry: TermTipEntry };

export const RecordText = ({ text, mode, lookup, onOpen, descriptionId }: RecordTextProps) => {
  const found = useMemo(() => findRecordIds({ text, lookup }), [text, lookup]);
  const [tip, setTip] = useState<ShownTip | null>(null);
  const firstMarker = useRef<HTMLSpanElement>(null);

  const show = ({ anchor, target }: { anchor: HTMLElement; target: RecordIdTarget }): void => {
    const entry = tipEntryOf(target);
    setTip(entry === null ? null : { anchor, entry });
  };
  const hide = (): void => {
    setTip(null);
  };

  // マーカーはフォーカスを受けないため、行のボタン（検索の結果は option）にフォーカスしたとき、行の中の最初の ID のツールチップを出す
  const firstTarget = found[0]?.target ?? null;
  useEffect(() => {
    const marker = firstMarker.current;
    const host = marker?.closest<HTMLElement>(MARKER_HOST) ?? null;
    if (mode !== "marker" || marker === null || host === null || firstTarget === null) return undefined;
    const onFocus = (): void => {
      const entry = tipEntryOf(firstTarget);
      setTip(entry === null ? null : { anchor: marker, entry });
    };
    const onBlur = (): void => {
      setTip(null);
    };
    host.addEventListener("focus", onFocus);
    host.addEventListener("blur", onBlur);
    return () => {
      host.removeEventListener("focus", onFocus);
      host.removeEventListener("blur", onBlur);
    };
  }, [mode, firstTarget]);

  const parts: ReactNode[] = [];
  let last = 0;
  for (const [position, { start, end, target }] of found.entries()) {
    if (start > last) parts.push(<Fragment key={`t${String(last)}`}>{text.slice(last, start)}</Fragment>);
    const key = `${String(start)}:${target.id}`;
    const label = text.slice(start, end);
    if (mode === "link") {
      parts.push(
        <a
          key={key}
          href={hashWith({ id: target.id, heading: null })}
          data-record-id={target.id}
          className="font-mono text-mark underline decoration-mark-line underline-offset-3"
          onMouseEnter={(event) => {
            show({ anchor: event.currentTarget, target });
          }}
          onMouseLeave={hide}
          onFocus={(event) => {
            show({ anchor: event.currentTarget, target });
          }}
          onBlur={hide}
          onClick={(event) => {
            event.preventDefault();
            hide();
            onOpen?.(target.id);
          }}
        >
          {label}
        </a>,
      );
    } else {
      parts.push(
        <span
          key={key}
          ref={position === 0 ? firstMarker : undefined}
          data-record-id={target.id}
          className="font-mono id-marker"
          onMouseEnter={(event) => {
            show({ anchor: event.currentTarget, target });
          }}
          onMouseLeave={hide}
        >
          {label}
        </span>,
      );
    }
    last = end;
  }
  if (last < text.length) parts.push(<Fragment key={`t${String(last)}`}>{text.slice(last)}</Fragment>);

  return (
    <>
      {parts}
      {mode === "marker" && descriptionId !== undefined && found.length > 0 ? (
        <span id={descriptionId} hidden>
          {found.map(({ target }) => describeTarget(target)).join("、")}
        </span>
      ) : null}
      {tip === null ? null : <TermTip entries={[tip.entry]} anchor={tip.anchor} on={{ open: (id) => onOpen?.(id), close: hide }} />}
    </>
  );
};
