// ネットワークの画面（画面設計『ネットワーク.tsx』）。全種類の項目を星として関連でつなぎ、3D で描く
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { GraphCanvas } from "@/features/graph/graph/components/graph-canvas";
import { LookSelect } from "@/features/graph/graph/components/look-select";
import { buildGraph, graphConditions, graphRows, shownGraphIds } from "@/features/graph/graph/graph-model";
import { useGraphLock } from "@/features/graph/graph/store";
import { FilterChips } from "@/shared/components/filter-chips";
import { FilterDrawer } from "@/shared/components/filter-drawer";
import { BUILTIN_LOOK } from "@/shared/core/display";
import { withoutKey } from "@/shared/core/filters";
import { drawerGroups } from "@/shared/core/list-rows";
import { isTyping, LOCK_QUERY, lockTap } from "@/shared/core/lock";
import { commentsQuery } from "@/shared/hooks/preview-queries";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useScreenFilters } from "@/shared/hooks/use-screen-filters";
import { usePrefs, writePrefs } from "@/shared/stores/prefs-store";

/** ロックの判定をする幅か（幅 900px 以下では詳細が全面に出るので、ロックしない） */
const isWide = (): boolean => typeof window.matchMedia === "function" && window.matchMedia(LOCK_QUERY).matches;

/** 重ねる面（ダイアログ・ポップオーバー・開いている一覧）を開いているか */
const overlayOpen = (): boolean => document.querySelector('[role="dialog"], dialog[open], [role="listbox"]') !== null || document.querySelector(":popover-open") !== null;

export type GraphScreenProps = { drawerOpen: boolean; onCloseDrawer: () => void };

export const GraphScreen = ({ drawerOpen, onCloseDrawer }: GraphScreenProps) => {
  const { search, openItem, closeItem } = usePreviewSearch();
  const { index } = useRecords();
  const { filters, setFilters } = useScreenFilters("graph");
  const comments = useQuery(commentsQuery());
  const prefs = usePrefs();
  const [locked, setLocked] = useGraphLock();
  const [shakeSignal, setShakeSignal] = useState(0);
  const filtersKey = JSON.stringify(filters);
  const shownIds = useMemo(() => (index === null ? new Set<string>() : shownGraphIds({ index, filters })), [index, filtersKey]); // eslint-disable-line react-hooks/exhaustive-deps -- 条件は中身が変わったときだけ作り直す
  const graph = useMemo(() => (index === null ? { nodes: [], links: [] } : buildGraph({ index, shownIds })), [index, shownIds]);
  const counts = useMemo(() => {
    const result: Record<string, number> = {};
    for (const { target } of comments.data?.status === 200 ? comments.data.data.items : []) {
      if (typeof target === "string") result[target] = (result[target] ?? 0) + 1;
    }
    return result;
  }, [comments.data]);
  const selectedId = search.id ?? null;
  // 効いているロック: ロックした項目を描いているときだけ
  const effectiveLock = locked !== null && shownIds.has(locked) ? locked : null;

  /** 玉か余白を押した（幅 900px 以下では押した項目を開くだけ） */
  const press = (pressed: string | null): void => {
    if (!isWide()) {
      if (pressed !== null) openItem(pressed);
      return;
    }
    const { action, locked: next } = lockTap({ locked: effectiveLock, pressed, open: selectedId });
    if (action === "shake") {
      setShakeSignal((value) => value + 1);
      return;
    }
    setLocked(next);
    if (action === "blank") closeItem();
    else if (action === "open" && pressed !== null && pressed !== selectedId) openItem(pressed);
  };

  // L キー: 詳細を開いている項目を押したのと同じ判定でロックを付け外しする
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      if (event.key.toLowerCase() !== "l" || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey || event.isComposing) return;
      if (isTyping(document.activeElement) || overlayOpen() || !isWide() || selectedId === null) return;
      press(selectedId);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
    };
  });

  if (index === null) return null;
  const conditions = graphConditions();
  const rows = graphRows(index);
  const defaultLook = index.data.settings.display?.network_look ?? BUILTIN_LOOK;
  const look = prefs.look ?? defaultLook;
  const labels = Object.fromEntries(conditions.map((condition) => [condition.key, condition.label]));
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <FilterChips filters={filters} labels={labels} onFilter={setFilters} />
      <div className="relative flex min-h-0 flex-1 flex-col">
        <GraphCanvas graph={graph} index={index} look={look} selectedId={selectedId} lockedId={effectiveLock} comments={counts} shakeSignal={shakeSignal} onPress={press} />
        {shownIds.size === 0 ? <p className="absolute inset-0 m-auto h-fit text-center text-muted-foreground">表示する項目はありません。</p> : null}
        <div className="absolute top-3 right-3">
          <LookSelect value={look} defaultLook={defaultLook} onChange={(next) => { writePrefs({ look: next }); }} />
        </div>
      </div>
      {drawerOpen ? (
        <FilterDrawer
          groups={drawerGroups({ rows, columns: conditions, conditions, filters })}
          selected={filters}
          total={rows.length}
          shown={shownIds.size}
          narrow={!isWide()}
          onToggleValue={(key, value) => {
            const current = filters[key] ?? [];
            const next = current.includes(value) ? current.filter((candidate) => candidate !== value) : [...current, value];
            setFilters(next.length === 0 ? withoutKey(filters, key) : { ...filters, [key]: next });
          }}
          onClearGroup={(key) => { setFilters(withoutKey(filters, key)); }}
          onClearAll={() => { setFilters({}); }}
          onClose={onCloseDrawer}
          onTextChange={() => undefined}
        />
      ) : null}
    </div>
  );
};
