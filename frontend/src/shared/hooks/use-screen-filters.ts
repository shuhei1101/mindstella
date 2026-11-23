// 画面の絞り込みの条件とタグの組み合わせ方を、URL とそのタブの保存領域で持つ（インターフェース定義『SPAを開く』の制約「保存した絞り込みの条件」）
import { useEffect, useRef } from "react";

import { defaultFilters, filtersFromSearch, filtersToSearch, TAG_FILTER_KEY, TEXT_FILTER_PREFIX, type Filters, type TagMatch } from "@/shared/core/filters";
import type { PreviewTab } from "@/shared/core/preview-search";
import { parseTagExpr, simpleTagsOf, tagExprOf, type PresetFilter } from "@/shared/core/presets";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { readScreenState, useScreenState, writeScreenState } from "@/shared/stores/screen-state-store";

/** 絞り込みを持たない画面 */
const FILTERLESS_TABS: readonly PreviewTab[] = ["overview", "settings"];

/** 画面の絞り込みの条件・タグの組み合わせ方と操作 */
export type ScreenFilters = {
  filters: Filters;
  tagMatch: TagMatch;
  /** 絞り込みの条件を書き換える。`push` を渡すと履歴に積み、渡さなければ置き換える（条件のチップ・画面へ入ったときの復元） */
  setFilters: (filters: Filters, options?: { push: boolean }) => void;
  /** タグの組み合わせ方を書き換えて履歴に積む */
  setTagMatch: (tagMatch: TagMatch) => void;
  /** タグの条件と列の条件をまとめて外し、履歴に 1 つ積む */
  clearAll: () => void;
  /** 列の文字の条件を書き換える。打ち終えた単位の最初の変更だけを履歴に積み、続く変更は置き換える */
  setTextFilter: (key: string, text: string) => void;
  /** 列の文字の条件の打ち終えた単位を終える（次の変更でまた 1 つ積む） */
  commitTextFilter: () => void;
  /** タグを条件に加えて履歴に積む（既にあれば何もしない）。絞り込みを持たない画面では `kindTab` の画面へ移って加える */
  addTag: (tag: string, kindTab?: PreviewTab) => void;
  /** 今のタグの条件の式。条件が無ければ null */
  tagExpr: PresetFilter | null;
  /** タグの条件を式で置き換える（ほかの条件は残す）。1 つの「含む」の条件は簡易の条件として持つ。null で解除する。`push` を渡すと履歴に積む */
  setTagExpr: (expr: PresetFilter | null, options?: { push: boolean }) => void;
};

export const useScreenFilters = (tab: PreviewTab): ScreenFilters => {
  const { search, setFilters: writeSearch, pushFilters, pushTagExpr, pushTagMatch, setTagCondition, pushTagCondition, openList } = usePreviewSearch();
  const filterless = FILTERLESS_TABS.includes(tab);
  const inUrl = Object.keys(search.f).length > 0 || search.tx !== undefined;
  const state = useScreenState();
  const saved = state.filters?.[tab];
  const savedTagMatch = state.tagMatch?.[tab] ?? "all";
  const savedTagExpr = state.tagExpr?.[tab];
  const filters = inUrl ? filtersFromSearch(search.f) : (saved ?? defaultFilters(tab));
  // URL に条件がある: URL の組み合わせ方（無ければ all）。無い: 保存した組み合わせ方
  const tagMatch: TagMatch = inUrl ? (search.tagmatch ?? "all") : savedTagMatch;
  // 式は URL の tx、無ければチェックの条件から作る
  const tagExpr: PresetFilter | null = search.tx === undefined ? ((filters[TAG_FILTER_KEY] ?? []).length > 0 ? tagExprOf({ tags: filters[TAG_FILTER_KEY] ?? [], match: tagMatch }) : null) : parseTagExpr(search.tx);
  // 保存した条件を URL に戻し終えた画面（画面へ入ったときに 1 度だけ戻す）
  const entered = useRef<PreviewTab | null>(null);
  // 列の文字の条件を打っている途中か（打ち終えた単位の 2 つ目からの変更は履歴に積まない）
  const typing = useRef(false);
  // URL と、そのタブの保存領域（ブラウザの sessionStorage）を同期する
  useEffect(() => {
    if (filterless) return;
    const current = readScreenState();
    const entering = entered.current !== tab;
    entered.current = tab;
    // 画面を移った: 文字の条件の打ち終えた単位を終える
    if (entering) typing.current = false;
    if (inUrl) {
      // URL に条件がある: 保存領域を URL に合わせる
      const tagExprs = Object.fromEntries(Object.entries(current.tagExpr ?? {}).filter(([name]) => name !== tab));
      writeScreenState({
        filters: { ...current.filters, [tab]: filtersFromSearch(search.f) },
        tagMatch: { ...current.tagMatch, [tab]: search.tagmatch ?? "all" },
        tagExpr: search.tx === undefined ? tagExprs : { ...tagExprs, [tab]: search.tx },
      });
    } else if (entering && ((saved !== undefined && Object.keys(saved).length > 0) || savedTagExpr !== undefined)) {
      // 画面へ入ったときに URL に無く保存した条件がある: 条件・組み合わせ方・式を 1 回の移動で URL に記載する
      setTagCondition({ f: filtersToSearch(saved ?? {}), tagmatch: savedTagMatch === "any" ? "any" : undefined, tx: savedTagExpr });
    } else if (!entering && (saved !== undefined || savedTagExpr !== undefined)) {
      // 同じ画面で URL の条件が無くなった（戻る・進む）: 保存した条件を除き、画面の既定の条件に戻す
      writeScreenState({
        filters: Object.fromEntries(Object.entries(current.filters ?? {}).filter(([name]) => name !== tab)),
        tagMatch: Object.fromEntries(Object.entries(current.tagMatch ?? {}).filter(([name]) => name !== tab)),
        tagExpr: Object.fromEntries(Object.entries(current.tagExpr ?? {}).filter(([name]) => name !== tab)),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- writeSearch は描画ごとに作り直される
  }, [tab, inUrl, JSON.stringify(search.f), search.tagmatch, search.tx]);
  return {
    filters,
    tagMatch,
    setFilters: (next, options) => {
      writeScreenState({ filters: { ...readScreenState().filters, [tab]: next } });
      // ドロワーから変えた: 履歴に積む。それ以外: 置き換える
      if (options?.push === true) pushFilters(filtersToSearch(next));
      else writeSearch(filtersToSearch(next));
    },
    setTagMatch: (next) => {
      writeScreenState({ tagMatch: { ...readScreenState().tagMatch, [tab]: next } });
      pushTagMatch(next === "any" ? "any" : undefined);
    },
    clearAll: () => {
      const tagExprs = Object.fromEntries(Object.entries(readScreenState().tagExpr ?? {}).filter(([name]) => name !== tab));
      writeScreenState({ filters: { ...readScreenState().filters, [tab]: {} }, tagMatch: { ...readScreenState().tagMatch, [tab]: "all" }, tagExpr: tagExprs });
      pushTagCondition({ f: {}, tagmatch: undefined, tx: undefined });
    },
    setTextFilter: (key, text) => {
      const name = `${TEXT_FILTER_PREFIX}${key}`;
      const next = text === "" ? Object.fromEntries(Object.entries(filters).filter(([filterKey]) => filterKey !== name)) : { ...filters, [name]: [text] };
      writeScreenState({ filters: { ...readScreenState().filters, [tab]: next } });
      // 打ち終えた単位の中: 置き換える。単位の最初の変更: 履歴に積んで単位を始める
      if (typing.current) {
        writeSearch(filtersToSearch(next));
      } else {
        typing.current = true;
        pushFilters(filtersToSearch(next));
      }
    },
    commitTextFilter: () => {
      typing.current = false;
    },
    addTag: (tag, kindTab) => {
      // 絞り込みを持たない画面: 項目の種類の画面へ移ってタグで絞る
      if (filterless) {
        if (kindTab !== undefined) openList(kindTab, { f: { [TAG_FILTER_KEY]: tag } });
        return;
      }
      // 式で絞っている: 今の式と押したタグの「含む」を and の束でまとめる
      if (tagExpr !== null && simpleTagsOf(tagExpr) === null) {
        const children = "and" in tagExpr ? tagExpr.and : [tagExpr];
        if (children.some((child) => "field" in child && child.op === "eq" && child.values.length === 1 && child.values[0] === tag)) return;
        pushTagExpr(JSON.stringify({ and: [...children, { field: "tags", op: "eq", values: [tag] }] }));
        return;
      }
      const tags = filters[TAG_FILTER_KEY] ?? [];
      if (tags.includes(tag)) return;
      pushFilters(filtersToSearch({ ...filters, [TAG_FILTER_KEY]: [...tags, tag] }));
    },
    tagExpr,
    setTagExpr: (expr, options) => {
      const rest = Object.fromEntries(Object.entries(filters).filter(([key]) => key !== TAG_FILTER_KEY));
      const simple = expr === null ? null : simpleTagsOf(expr);
      const next = simple === null || simple.tags.length === 0 ? rest : { ...rest, [TAG_FILTER_KEY]: simple.tags };
      const tagExprs = Object.fromEntries(Object.entries(readScreenState().tagExpr ?? {}).filter(([name]) => name !== tab));
      const tx = expr === null || simple !== null ? undefined : JSON.stringify(expr);
      writeScreenState({ filters: { ...readScreenState().filters, [tab]: next }, tagMatch: { ...readScreenState().tagMatch, [tab]: simple?.match ?? "all" }, tagExpr: tx === undefined ? tagExprs : { ...tagExprs, [tab]: tx } });
      const condition = { f: filtersToSearch(next), tagmatch: simple?.match === "any" && simple.tags.length > 1 ? ("any" as const) : undefined, tx };
      // ドロワーから変えた: 履歴に積む。それ以外（条件のチップ）: 置き換える
      if (options?.push === true) pushTagCondition(condition);
      else setTagCondition(condition);
    },
  };
};
