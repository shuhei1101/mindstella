// ネットワークの玉と線、描く項目、絞る条件（今の画面の `graph/graph.ts` の計算と同じ振る舞い）
import type { Filters } from "@/shared/core/filters";
import { filterRows, type ListColumn } from "@/shared/core/list-rows";
import { DECISION_STATUSES, DOC_STATUSES, KIND_KEYS, KIND_LABEL, TASK_STATUSES, tagNames, type Item, type Kind, type RecordIndex } from "@/shared/core/records";

/** 線の種類 */
export type LinkType = "depends" | "related" | "source" | "for";

/** ネットワークの玉 */
export type GraphNode = { id: string; kind: Kind };

/** ネットワークの線（`source` が指す側、`target` が指される側） */
export type GraphLink = { source: string; target: string; type: LinkType };

/** ネットワークの玉と線 */
export type Graph = { nodes: GraphNode[]; links: GraphLink[] };

/** 条件で絞る行（索引の項目に ID を足したもの） */
export type GraphRow = { id: string; kind: Kind; item: Item };

/** 項目が別の項目を指すキー → 線の種類 */
const LINK_KEYS: readonly ["depends_on" | "for" | "sources" | "related", LinkType][] = [
  ["depends_on", "depends"],
  ["for", "for"],
  ["sources", "source"],
  ["related", "related"],
];

/** 状態を持つ種類（検討事項・タスク・資料）の状態を重ねた並び（状態の条件の値の順） */
const GRAPH_STATUS_ORDER: readonly string[] = [...new Set([...DECISION_STATUSES, ...TASK_STATUSES, ...DOC_STATUSES])];

/** 渡した ID の項目を玉に、関連を線にして返す（両端のどちらかが渡していない項目か記録に無い線は含めない） */
export const buildGraph = ({ index, shownIds }: { index: RecordIndex; shownIds: Set<string> }): Graph => {
  const nodes: GraphNode[] = [];
  for (const [id, { kind }] of index.byId) if (shownIds.has(id)) nodes.push({ id, kind });
  const shown = new Set(nodes.map((node) => node.id));
  const links: GraphLink[] = [];
  const seen = new Set<string>();
  for (const { id: source } of nodes) {
    const item = index.byId.get(source)?.item;
    if (item === undefined) continue;
    for (const [key, type] of LINK_KEYS) {
      for (const target of item[key] ?? []) {
        const identity = `${type}|${source}|${target}`;
        // 自分自身へ・渡していないか記録に無い項目へ・同じ線の重なりは作らない
        if (source === target || !shown.has(target) || seen.has(identity)) continue;
        seen.add(identity);
        links.push({ source, target, type });
      }
    }
  }
  return { nodes, links };
};

/** ネットワークで絞る条件（種類・状態・タグ）の定義を返す */
export const graphConditions = (): ListColumn<Pick<GraphRow, "kind" | "item">>[] => [
  { key: "type", label: "種類", order: KIND_KEYS.map((kind) => KIND_LABEL[kind]), get: (row) => KIND_LABEL[row.kind] },
  { key: "status", label: "状態", order: GRAPH_STATUS_ORDER, get: (row) => row.item.status },
  { key: "tags", label: "タグ", get: (row) => tagNames(row.item.tags) },
];

/** 索引の項目を条件で絞る行にする */
export const graphRows = (index: RecordIndex): GraphRow[] => [...index.byId].map(([id, entry]) => ({ id, ...entry }));

/** 絞り込みの条件に合う項目の ID（ネットワークが描く玉。ロックした項目を描いているかの判定にも使う） */
export const shownGraphIds = ({ index, filters }: { index: RecordIndex; filters: Filters }): Set<string> =>
  new Set(filterRows({ rows: graphRows(index), columns: graphConditions(), filters }).map((row) => row.id));
