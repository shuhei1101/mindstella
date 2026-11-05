// 24px の枠に描いた線のアイコンと、状態の 10px の印（今の画面の `core/dom.ts` と同じ絵）
import type { ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

/** アイコンの名前 → SVG の中身 */
const ICONS = {
  map: (
    <>
      <circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.5 12h3l4-5M11.5 12l4 5"/>
    </>
  ),
  board: (
    <>
      <rect x="3" y="4" width="5" height="16" rx="1"/><rect x="10" y="4" width="5" height="11" rx="1"/><rect x="17" y="4" width="4" height="7" rx="1"/>
    </>
  ),
  back: <path d="m15 6-6 6 6 6" />,
  star: <path d="m12 3 2.7 5.8 6.3.8-4.6 4.3 1.2 6.2-5.6-3.1-5.6 3.1 1.2-6.2L3 9.6l6.3-.8z" />,
  code: <path d="m8 7-5 5 5 5M16 7l5 5-5 5" />,
  graph: <><circle cx="6" cy="6" r="2" /><circle cx="18" cy="8" r="2" /><circle cx="10" cy="18" r="2" /><path d="M8 6.5 16 7.5M7 8l2.5 8M16.5 9.5 11.5 16.5" /></>,
  cards: (
    <>
      <rect x="3" y="4" width="8" height="7" rx="1"/><rect x="13" y="4" width="8" height="7" rx="1"/><rect x="3" y="13" width="8" height="7" rx="1"/><rect x="13" y="13" width="8" height="7" rx="1"/>
    </>
  ),
  table: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 10h18M9 10v10"/>
    </>
  ),
  plus: (
    <>
      <path d="M12 5v14M5 12h14"/>
    </>
  ),
  minus: (
    <>
      <path d="M5 12h14"/>
    </>
  ),
  changed: (
    <>
      <circle cx="12" cy="12" r="5"/>
    </>
  ),
  bubble: (
    <>
      <path d="M5 4h14a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-7l-5 4v-4H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"/>
    </>
  ),
  main: (
    <>
      <circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3.5" fill="currentColor"/>
    </>
  ),
  mainOff: (
    <>
      <circle cx="12" cy="12" r="8"/>
    </>
  ),
  trash: (
    <>
      <path d="M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13"/><path d="M10 11v6M14 11v6"/>
    </>
  ),
  check: (
    <>
      <path d="m5 12 5 5 9-10"/>
    </>
  ),
  edit: (
    <>
      <path d="m4 20 1-4L16 5l3 3L8 19Z"/><path d="m14 7 3 3"/>
    </>
  ),
  expand: (
    <>
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
    </>
  ),
  shrink: (
    <>
      <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/>
    </>
  ),
  copy: (
    <>
      <rect x="9" y="9" width="12" height="12" rx="1"/><path d="M5 15V4a1 1 0 0 1 1-1h11"/>
    </>
  ),
  download: (
    <>
      <path d="M12 4v11M7 10l5 5 5-5"/><path d="M5 20h14"/>
    </>
  ),
  cols: (
    <>
      <rect x="3" y="4" width="18" height="16" rx="1"/><path d="M9 4v16M15 4v16"/>
    </>
  ),
  updown: (
    <>
      <path d="m8 9 4-4 4 4M8 15l4 4 4-4"/>
    </>
  ),
  lock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </>
  ),
  unlock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/>
    </>
  ),
  save: (
    <>
      <path d="M5 4h11l3 3v13H5Z"/><path d="M8 4v5h7V4M8 20v-6h8v6"/>
    </>
  ),
  undo: (
    <>
      <path d="M9 7 4 12l5 5"/><path d="M4 12h10a5 5 0 0 1 0 10h-2"/>
    </>
  ),
  arrow: (
    <>
      <path d="M5 12h14M13 6l6 6-6 6"/>
    </>
  ),
  link: (
    <>
      <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>
    </>
  ),
  sun: (
    <>
      <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
    </>
  ),
  moon: (
    <>
      <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/>
    </>
  ),
  x: (
    <>
      <path d="M18 6 6 18M6 6l12 12"/>
    </>
  ),
  chev: (
    <>
      <path d="m9 6 6 6-6 6"/>
    </>
  ),
  filter: (
    <>
      <path d="M4 5h16l-6 7.5V19l-4-2v-4.5Z"/>
    </>
  ),
  layers: (
    <>
      <path d="m12 3 9 5-9 5-9-5Z"/><path d="m3 13 9 5 9-5"/>
    </>
  ),
  history: (
    <>
      <path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>
    </>
  ),
  comment: (
    <>
      <path d="M4 5h16v11H10l-5 4v-4H4Z"/><path d="M8 9h8M8 12.5h5"/>
    </>
  ),
  sliders: (
    <>
      <path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>
    </>
  ),
  offline: (
    <>
      <path d="M3 3l18 18"/><path d="M8.5 8.6A4.5 4.5 0 0 0 7 17h10.5M16 10.2A4.5 4.5 0 0 1 20.2 16"/>
    </>
  ),
  alert: (
    <>
      <path d="M12 3 2 20h20Z"/><path d="M12 10v4M12 17h.01"/>
    </>
  ),
  network: (
    <>
      <path d="M4 18.5 10 13.5l5 3M10 13.5 7.5 6.5M15 16.5l3.2-6.6" strokeWidth="1.15"/><circle cx="4" cy="18.5" r="2" fill="currentColor" stroke="none"/><circle cx="10" cy="13.5" r="2.2" fill="currentColor" stroke="none"/><circle cx="15" cy="16.5" r="1.8" fill="currentColor" stroke="none"/><circle cx="7.5" cy="6.5" r="1.8" fill="currentColor" stroke="none"/><path d="m19 1.8 1.05 3.15L23.2 6l-3.15 1.05L19 10.2l-1.05-3.15L14.8 6l3.15-1.05Z" fill="currentColor" stroke="none"/>
    </>
  ),
  flag: (
    <>
      <path d="M5 21V4M5 4h11l-2 4 2 4H5"/>
    </>
  ),
  pause: (
    <>
      <path d="M8 5v14M16 5v14"/>
    </>
  ),
  play: (
    <>
      <path d="m7 5 12 7-12 7Z"/>
    </>
  ),
  next: (
    <>
      <circle cx="12" cy="12" r="9"/><path d="M10 8l4 4-4 4"/>
    </>
  ),
  follow: (
    <>
      <path d="M5 5v6a4 4 0 0 0 4 4h10"/><path d="m15 11 4 4-4 4"/>
    </>
  ),
  box: (
    <>
      <path d="M3 7l9-4 9 4v10l-9 4-9-4Z"/><path d="M3 7l9 4 9-4M12 11v10"/>
    </>
  ),
  checked: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 5-6"/>
    </>
  ),
  unchecked: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="3"/>
    </>
  ),
  home: (
    <>
      <path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>
    </>
  ),
  decision: (
    <>
      <circle cx="12" cy="12" r="8"/><path d="m9 12 2 2 4-4"/>
    </>
  ),
  task: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>
    </>
  ),
  research: (
    <>
      <circle cx="10.5" cy="10.5" r="6"/><path d="m15 15 5 5"/><path d="M8 10.5h5"/>
    </>
  ),
  doc: (
    <>
      <path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v4h4"/>
    </>
  ),
  term: (
    <>
      <path d="M4 5h11a3 3 0 0 1 3 3v12H7a3 3 0 0 1-3-3Z"/><path d="M4 17a3 3 0 0 1 3-3h11"/>
    </>
  ),
  note: (
    <>
      <path d="M5 4h14v12l-4 4H5Z"/><path d="M15 20v-4h4"/>
    </>
  ),
  log: (
    <>
      <path d="M4 6h16v10H9l-5 4Z"/>
    </>
  ),
} satisfies Record<string, ReactNode>;

export type IconName = keyof typeof ICONS;

/** 線のアイコン（読み上げから外す装飾）。大きさは className で変える */
export const Icon = ({ name, className }: { name: IconName; className?: string }) => (
  <svg
    className={cn("size-4 flex-none fill-none stroke-current", className)}
    width="16"
    height="16"
    viewBox="0 0 24 24"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {ICONS[name]}
  </svg>
);

/** 状態 → 10px の枠に描く印（色に加えて形でも区別する） */
const MARKS: Record<string, ReactNode> = {
  決定済み: (
    <>
      <circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>
    </>
  ),
  完了: (
    <>
      <circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/><path d="m2.8 5.1 1.5 1.5 3-3" stroke="var(--card)" strokeWidth="1.4" fill="none"/>
    </>
  ),
  未決定: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" strokeWidth="1.6"/>
    </>
  ),
  未着手: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" strokeWidth="1.6"/>
    </>
  ),
  進行中: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" strokeWidth="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>
    </>
  ),
  要見直し: (
    <>
      <path d="M5 .3 9.7 5 5 9.7.3 5Z" fill="var(--st-review)"/>
    </>
  ),
  保留: (
    <>
      <rect x="1.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/><rect x="6.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/>
    </>
  ),
  未整理: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-loose)" strokeWidth="1.6" strokeDasharray="2 1.6"/>
    </>
  ),
  取り下げ: (
    <>
      <path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" strokeWidth="1.6"/>
    </>
  ),
  対象外: (
    <>
      <path d="M1 5h8" stroke="var(--st-off)" strokeWidth="1.8"/>
    </>
  ),
  中止: (
    <>
      <path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" strokeWidth="1.6"/>
    </>
  ),
  下書き: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" strokeWidth="1.6" strokeDasharray="2 1.6"/>
    </>
  ),
  確認中: (
    <>
      <circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" strokeWidth="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>
    </>
  ),
  完成: (
    <>
      <circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>
    </>
  ),
};

/** 状態の印。知らない状態は描かない */
export const StatusMark = ({ status }: { status: string | undefined }) => {
  const body = status === undefined ? undefined : MARKS[status];
  if (body === undefined) return null;
  return (
    <svg className="size-2.5 flex-none overflow-visible" viewBox="0 0 10 10" aria-hidden="true">
      {body}
    </svg>
  );
};
