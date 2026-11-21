// 状態のマーカーの形状。React の部品と、React の外で組む本文のツールチップが同じ形状を使用する

/** 状態 → 10px の枠に描くマーカーの SVG の中身（色に加えて形でも区別する） */
const STATUS_MARK_MARKUP: Record<string, string> = {
  決定済み: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
  完了: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/><path d="m2.8 5.1 1.5 1.5 3-3" stroke="var(--card)" stroke-width="1.4" fill="none"/>',
  未決定: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/>',
  未着手: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6"/>',
  進行中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
  要見直し: '<path d="M5 .3 9.7 5 5 9.7.3 5Z" fill="var(--st-review)"/>',
  保留: '<rect x="1.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/><rect x="6.2" y="1" width="2.6" height="8" fill="var(--st-hold)"/>',
  未整理: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-loose)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
  取り下げ: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
  対象外: '<path d="M1 5h8" stroke="var(--st-off)" stroke-width="1.8"/>',
  中止: '<path d="m1.5 1.5 7 7M8.5 1.5l-7 7" stroke="var(--st-off)" stroke-width="1.6"/>',
  下書き: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-off)" stroke-width="1.6" stroke-dasharray="2 1.6"/>',
  確認中: '<circle cx="5" cy="5" r="3.8" fill="none" stroke="var(--st-open)" stroke-width="1.6"/><path d="M5 1.2a3.8 3.8 0 0 1 0 7.6Z" fill="var(--st-open)"/>',
  完成: '<circle cx="5" cy="5" r="4.5" fill="var(--st-done)"/>',
};

/** 状態のマーカーの SVG の中身。知らない状態は null */
export const statusMarkMarkup = (status: string | undefined): string | null => (status === undefined ? null : (STATUS_MARK_MARKUP[status] ?? null));

/** 状態のマーカーの SVG の要素（React の外で組む本文で使う）。知らない状態は null */
export const statusMarkElement = (status: string | undefined): SVGSVGElement | null => {
  const markup = statusMarkMarkup(status);
  if (markup === null) return null;
  const holder = document.createElement("template");
  holder.innerHTML = `<svg class="st-mark" width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">${markup}</svg>`;
  return holder.content.firstElementChild as SVGSVGElement;
};
