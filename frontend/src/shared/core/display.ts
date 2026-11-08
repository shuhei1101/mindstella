// 表示の設定の計算（今の画面の `components/settings-panel.ts`・`settings-confirm.ts` と、`app.ts` の既定に戻すと同じ振る舞い）
import type { NetworkLook, SettingsDisplay } from "@/shared/api/generated/model";
import { defaultFilters, type Filters } from "@/shared/core/filters";
import type { PreviewTab } from "@/shared/core/preview-search";
import { KIND_KEYS, KIND_LABEL, type Kind } from "@/shared/core/records";
import type { Prefs } from "@/shared/stores/prefs-store";
import type { Theme } from "@/shared/stores/theme-store";

/** ワークスペースの既定も個人の上書きも無いときの見た目 */
export const BUILTIN_LOOK: NetworkLook = "deep";

/** 見た目 → 画面に出す名前 */
const LOOK_LABEL = { glow: "グロウ", starlight: "星の光", constellation: "星図", deep: "深宇宙", dust: "星屑" } as const satisfies Record<NetworkLook, string>;

/** 区画「詳細に表示するもの」の項目の名前 */
export const MINIMAP_LABEL = "差分のミニマップ";
export const BODY_VIEW_LABELS = { pin: "表の列の固定", head: "表の見出しの固定", stripes: "表のしま模様", fold: "セクションの折りたたみ" } as const;
const BODY_LAYOUT_LABEL = "本文の差分の並べ方";
const REVIEW_ORDER_LABEL = "コメントの並び";

/** 見た目の名前 */
export const lookLabel = (look: NetworkLook): string => LOOK_LABEL[look];

/** 表示する種類を、外した種類の名前で書く（全て出すときは「すべて表示」） */
export const kindsText = (kinds: ReadonlySet<Kind>): string => {
  const hidden = KIND_KEYS.filter((kind) => !kinds.has(kind)).map((kind) => KIND_LABEL[kind]);
  return hidden.length > 0 ? `${hidden.join("・")}を表示しない` : "すべて表示";
};

/** 絞り込みの条件が画面の既定と同じか */
const sameFilters = (a: Filters, b: Filters): boolean => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());

/** この端末で変えている項目の名前（見た目・種類・ライト / ダーク・表の列・絞り込み・差分のミニマップ・本文の見せ方・本文の差分の並べ方・コメントの並びの順） */
export const overrideNames = ({ prefs, theme }: { prefs: Prefs; theme: Theme | null }): string[] => {
  const columns = prefs.columns ?? {};
  const filters = prefs.filters ?? {};
  return [
    ...(prefs.look === null || prefs.look === undefined ? [] : ["ネットワークの見た目"]),
    ...(prefs.kinds === null || prefs.kinds === undefined ? [] : ["表示する種類"]),
    ...(theme === null ? [] : ["ライト / ダーク"]),
    ...KIND_KEYS.filter((kind) => columns[kind] !== undefined).map((kind) => `表の列（${KIND_LABEL[kind]}）`),
    ...KIND_KEYS.filter((kind) => filters[kind] !== undefined && !sameFilters(filters[kind], defaultFilters(kind as PreviewTab))).map((kind) => `絞り込み（${KIND_LABEL[kind]}）`),
    ...(prefs.minimap === false ? [MINIMAP_LABEL] : []),
    ...(prefs.tablePin === false ? [BODY_VIEW_LABELS.pin] : []),
    ...(prefs.tableHead === false ? [BODY_VIEW_LABELS.head] : []),
    ...(prefs.tableStripes === true ? [BODY_VIEW_LABELS.stripes] : []),
    ...(prefs.sectionFold === false ? [BODY_VIEW_LABELS.fold] : []),
    ...(prefs.bodyLayout === "side" ? [BODY_LAYOUT_LABEL] : []),
    ...(prefs.reviewOrder === "oldest" ? [REVIEW_ORDER_LABEL] : []),
  ];
};

/** 既定に戻した保存領域の値（`diffSel`・`commentsPinned`・`commentFormClosed` と知らない項目は残し、渡した値は変えない） */
export const resetPrefs = (prefs: Record<string, unknown>): Record<string, unknown> => ({
  ...prefs,
  theme: null,
  look: null,
  kinds: null,
  columns: {},
  filters: {},
  minimap: null,
  bodyLayout: null,
  reviewOrder: null,
  tablePin: null,
  tableHead: null,
  tableStripes: null,
  sectionFold: null,
});

/** ワークスペースの既定（見た目は無ければ `deep`、表示する種類は無ければ全ての種類） */
export const displayDefaults = (display: SettingsDisplay | undefined): { look: NetworkLook; kinds: Kind[] } => ({
  look: display?.network_look ?? BUILTIN_LOOK,
  kinds: [...(display?.visible_kinds ?? KIND_KEYS)],
});
