// 記録の文字を描き、項目の ID・スレッドの ID をリンクかマーカーにする部品（モック）
import { Fragment } from "react";

import { hashWith } from "@/shared/core/body-links";

/** ID が指す項目・スレッドの、ツールチップに出す中身 */
export type RecordIdTarget = { id: string; title: string; kindLabel: string; status?: string };

/** ID から記録の項目・スレッドを参照する。記録に無い ID は `null` */
export type LookupRecordId = (id: string) => RecordIdTarget | null;

/** ID を押したとき */
export type OpenRecordId = (id: string) => void;

/** `link` は押せない場所（見出し・関係する項目のタイトル）、`marker` は押す要素の中（カード・行・検索の結果） */
export type RecordTextMode = "link" | "marker";

type RecordTextProps = {
  text: string;
  mode: RecordTextMode;
  lookup: LookupRecordId;
  onOpen?: OpenRecordId;
  /** `marker` のとき、行の中の ID の説明を描く要素の id。行のボタンの `aria-describedby` に指定する */
  descriptionId?: string;
};

type TextPart = { text: string; target: RecordIdTarget | null };

/** スレッドの ID と項目の ID（前後が英数字のものは当てない。本文のリンクと同じ判定） */
const RECORD_ID_PATTERN = /(?<![A-Za-z0-9-])(?:TH-[0-9]+(?:-[0-9]+)?|[A-Z]+-[0-9]+)(?![0-9])/g;

/** 記録の文字を、記録にある ID と文字の並びに分ける */
const splitText = ({ text, lookup }: { text: string; lookup: LookupRecordId }): TextPart[] => {
  const parts: TextPart[] = [];
  let last = 0;
  for (const match of text.matchAll(RECORD_ID_PATTERN)) {
    const target = lookup(match[0]);
    if (target === null) continue;
    if (match.index > last) parts.push({ text: text.slice(last, match.index), target: null });
    parts.push({ text: match[0], target });
    last = match.index + match[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), target: null });
  return parts;
};

/** ツールチップと読み上げの説明の文 */
const describe = (target: RecordIdTarget): string => [`${target.title}（${target.id}）`, target.kindLabel, target.status].filter((value) => value !== undefined).join(" ");

export const RecordText = ({ text, mode, lookup, onOpen, descriptionId }: RecordTextProps) => {
  const parts = splitText({ text, lookup });
  const targets = parts.flatMap((part) => (part.target === null ? [] : [part.target]));
  return (
    <>
      {parts.map((part, position) => {
        const key = `${String(position)}:${part.text}`;
        const target = part.target;
        if (target === null) return <Fragment key={key}>{part.text}</Fragment>;
        if (mode === "link") {
          return (
            <a
              key={key}
              href={hashWith({ id: target.id, heading: null })}
              data-record-id={target.id}
              title={describe(target)}
              className="font-mono text-mark underline decoration-mark-line underline-offset-3"
              onClick={(event) => {
                event.preventDefault();
                onOpen?.(target.id);
              }}
            >
              {part.text}
            </a>
          );
        }
        return (
          <span key={key} data-record-id={target.id} title={describe(target)} className="font-mono underline decoration-subtle-foreground decoration-dotted underline-offset-4">
            {part.text}
          </span>
        );
      })}
      {mode === "marker" && descriptionId !== undefined && targets.length > 0 ? (
        <span id={descriptionId} hidden>
          {targets.map(describe).join("、")}
        </span>
      ) : null}
    </>
  );
};
