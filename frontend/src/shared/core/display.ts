// 表示の設定の計算（今の画面の `components/settings-panel.ts`・`settings-confirm.ts` と、`app.ts` の既定に戻すと同じ振る舞い）
import type { SettingsDisplay } from "@/shared/api/generated/model";
import { defaultFilters, type Filters } from "@/shared/core/filters";
import type { PreviewTab } from "@/shared/core/preview-search";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import type { Prefs } from "@/shared/stores/prefs-store";
import type { Theme } from "@/shared/stores/theme-store";

/** 区画「詳細に表示するもの」の項目の名前 */
export const MINIMAP_LABEL = "差分のミニマップ";
export const BODY_VIEW_LABELS = { fold: "セクションの折りたたみ" } as const;
const BODY_LAYOUT_LABEL = "本文の差分の並べ方";
const REVIEW_ORDER_LABEL = "コメントの並び";

/** 区画「コメントの入力」の「レビューに追加」の後のフォーカスの名前 */
export const FOCUS_AFTER_ADD_LABEL = "レビューに追加した後のフォーカス";

/** 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」） */
export const kindsText = (kinds: ReadonlySet<Kind>): string => {
  const hidden = KIND_KEYS.filter((kind) => !kinds.has(kind)).map((kind) => KIND_LABEL[kind]);
  return hidden.length > 0 ? `${hidden.join("・")}を表示しない` : "すべて表示";
};

/** 絞り込みの条件が画面の既定と同じか */
const sameFilters = (a: Filters, b: Filters): boolean => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());

/** この端末で変えている項目の名前（種類・ライト / ダーク・表の列・絞り込み・差分のミニマップ・本文の見せ方・本文の差分の並べ方・コメントの並び・「レビューに追加」の後のフォーカスの順） */
export const overrideNames = ({ prefs, theme }: { prefs: Prefs; theme: Theme | null }): string[] => {
  const columns = prefs.columns ?? {};
  const filters = prefs.filters ?? {};
  return [
    ...(prefs.kinds === null || prefs.kinds === undefined ? [] : ["表示する種類"]),
    ...(theme === null ? [] : ["ライト / ダーク"]),
    ...KIND_KEYS.filter((kind) => columns[kind] !== undefined).map((kind) => `表の列（${KIND_LABEL[kind]}）`),
    ...KIND_KEYS.filter((kind) => filters[kind] !== undefined && !sameFilters(filters[kind], defaultFilters(kind as PreviewTab))).map((kind) => `絞り込み（${KIND_LABEL[kind]}）`),
    ...(prefs.minimap === false ? [MINIMAP_LABEL] : []),
    ...(prefs.sectionFold === false ? [BODY_VIEW_LABELS.fold] : []),
    ...(prefs.bodyLayout === "side" ? [BODY_LAYOUT_LABEL] : []),
    ...(prefs.reviewOrder === "oldest" ? [REVIEW_ORDER_LABEL] : []),
    ...(prefs.focusAfterAdd === "input" || prefs.focusAfterAdd === "none" ? [FOCUS_AFTER_ADD_LABEL] : []),
  ];
};

/** 既定に戻した保存領域の値（`diffSel`・`commentsPinned`・`commentFormClosed` と知らない項目は残し、渡した値は変えない） */
export const resetPrefs = (prefs: Record<string, unknown>): Record<string, unknown> => ({
  ...prefs,
  theme: null,
  kinds: null,
  columns: {},
  filters: {},
  minimap: null,
  bodyLayout: null,
  reviewOrder: null,
  focusAfterAdd: null,
  sectionFold: null,
});

/** ワークスペースの既定（表示する種類は無ければ全ての種類） */
export const displayDefaults = (display: SettingsDisplay | undefined): { kinds: Kind[] } => ({
  kinds: [...(display?.visible_kinds ?? KIND_KEYS)],
});

/** 「レビューに追加」の後のフォーカスの移動先。上書きが無ければ（自動）端末の主な入力がタッチなら「レビューに追加」、それ以外は入力欄 */
export const focusAfterAddTarget = (prefs: Prefs, coarse: boolean): "input" | "submit" => {
  if (prefs.focusAfterAdd === "input") return "input";
  if (prefs.focusAfterAdd === "none") return "submit";
  return coarse ? "submit" : "input";
};
