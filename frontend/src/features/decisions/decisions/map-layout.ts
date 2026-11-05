// 検討事項のマップの木の組み立てと配置。対象 → カテゴリー → フェーズ → 検討事項の順に、項目を持つ節だけを描く
import { compareIds, type Item, type Settings } from "@/shared/core/records";

/** 節の種類 */
export type MapNodeKind = "target" | "category" | "phase" | "item";

/** マップの節（ELK に渡し、配置された座標が入って戻る） */
export type MapNode = { id: string; width: number; height: number; kind: MapNodeKind; label: string; item?: Item; x?: number; y?: number };

/** マップの枝 */
export type MapEdge = {
  id: string;
  sources: string[];
  targets: string[];
  sections?: { startPoint: { x: number; y: number }; endPoint: { x: number; y: number }; bendPoints?: { x: number; y: number }[] }[];
};

/** ELK に渡すグラフ */
export type MapGraph = { id: string; layoutOptions: Record<string, string>; nodes: MapNode[]; edges: MapEdge[]; width?: number; height?: number };

/** ELK の口 */
export type Elk = { layout: (graph: unknown) => Promise<unknown> };

const NODE_SIZE: Record<MapNodeKind, [number, number]> = { target: [130, 40], category: [150, 34], phase: [118, 26], item: [268, 48] };

const UNSET = "（未設定）";

const ELK_OPTIONS: Record<string, string> = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.edgeRouting": "ORTHOGONAL",
  "elk.layered.spacing.nodeNodeBetweenLayers": "36",
  "elk.spacing.nodeNode": "10",
  "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
  "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
  "elk.layered.nodePlacement.bk.fixedAlignment": "BALANCED",
  "elk.padding": "[top=24,left=24,bottom=24,right=24]",
};

const unique = (values: string[]): string[] => [...new Set(values)];

const rankIn = (list: readonly string[], name: string): number => {
  const position = list.indexOf(name);
  return position < 0 ? list.length : position;
};

/** 渡した検討事項だけで木を組む */
export const buildMapGraph = (items: readonly Item[], settings: Settings): MapGraph => {
  const shown = [...items].sort((a, b) => compareIds(a.id, b.id));
  const targetOf = (item: Item): string => settings.categories.find((category) => category.name === item.category)?.target ?? item.target ?? UNSET;
  const categoryOf = (item: Item): string => item.category ?? UNSET;
  const phaseOf = (item: Item): string => item.phase ?? UNSET;
  const nodes: MapNode[] = [];
  const edges: MapEdge[] = [];
  const add = (id: string, kind: MapNodeKind, label: string, parent: string | null, item?: Item): void => {
    const [width, height] = NODE_SIZE[kind];
    nodes.push({ id, width, height, kind, label, ...(item === undefined ? {} : { item }) });
    if (parent !== null) edges.push({ id: `${parent}>${id}`, sources: [parent], targets: [id] });
  };
  const targetNames = settings.targets.map((target) => target.name);
  const categoryNames = settings.categories.map((category) => category.name);
  for (const target of unique(shown.map(targetOf)).sort((a, b) => rankIn(targetNames, a) - rankIn(targetNames, b))) {
    const targetId = `target:${target}`;
    add(targetId, "target", target, null);
    const ofTarget = shown.filter((item) => targetOf(item) === target);
    for (const category of unique(ofTarget.map(categoryOf)).sort((a, b) => rankIn(categoryNames, a) - rankIn(categoryNames, b))) {
      const categoryId = `category:${target}/${category}`;
      add(categoryId, "category", category, targetId);
      const ofCategory = ofTarget.filter((item) => categoryOf(item) === category);
      for (const phase of unique(ofCategory.map(phaseOf)).sort((a, b) => rankIn(settings.phases, a) - rankIn(settings.phases, b))) {
        const phaseId = `phase:${target}/${category}/${phase}`;
        add(phaseId, "phase", phase, categoryId);
        for (const item of ofCategory.filter((candidate) => phaseOf(candidate) === phase)) add(item.id, "item", item.title, phaseId, item);
      }
    }
  }
  return { id: "graph", layoutOptions: ELK_OPTIONS, nodes, edges };
};

/** 配置を求める（ELK は節を `children` で受ける） */
export const layoutMap = async (graph: MapGraph, elk: Elk): Promise<MapGraph> => {
  const { nodes, ...rest } = graph;
  const laid = (await elk.layout({ ...rest, children: nodes })) as Omit<MapGraph, "nodes"> & { children: MapNode[] };
  return { ...laid, nodes: laid.children };
};

/** 前提 → 後続の線の道筋（同じ列どうしは、節の右側にふくらむ弧でつなぐ） */
export const dependencyPath = (from: MapNode, to: MapNode): string => {
  const fromX = (from.x ?? 0) + from.width;
  const fromY = (from.y ?? 0) + from.height / 2;
  const toY = (to.y ?? 0) + to.height / 2;
  if (Math.abs((from.x ?? 0) - (to.x ?? 0)) < 10) {
    const bulge = 28 + Math.min(60, Math.abs(toY - fromY) / 6);
    return `M${String(fromX)},${String(fromY)} C${String(fromX + bulge)},${String(fromY)} ${String(fromX + bulge)},${String(toY)} ${String(fromX)},${String(toY)}`;
  }
  const toX = to.x ?? 0;
  const reach = Math.max(60, Math.abs(toX - fromX) / 2);
  return `M${String(fromX)},${String(fromY)} C${String(fromX + reach)},${String(fromY)} ${String(toX - reach)},${String(toY)} ${String(toX)},${String(toY)}`;
};

const WHEEL_FACTOR = 1.12;

/** 倍率の範囲と 1 回の幅 */
export const ZOOM = { min: 0.4, max: 1.5, step: 0.15 };

/** ホイール 1 回で変えた後の倍率と、マウスの下の点を残すスクロールの位置を返す */
export const wheelZoom = ({ scale, deltaY, point, scroll }: { scale: number; deltaY: number; point: { x: number; y: number }; scroll: { left: number; top: number } }) => {
  const factor = deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR;
  const next = Math.min(ZOOM.max, Math.max(Math.min(ZOOM.min, scale), scale * factor));
  const ratio = next / scale;
  return { scale: next, scroll: { left: (scroll.left + point.x) * ratio - point.x, top: (scroll.top + point.y) * ratio - point.y } };
};
