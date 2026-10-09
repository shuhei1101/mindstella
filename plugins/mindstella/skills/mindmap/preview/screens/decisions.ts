// 検討事項。マップ（既定）・ボード・表で見る。マップは対象 → カテゴリー → フェーズ → 検討事項の木を ELK で配置して描く。

namespace MindmapPreview {
  /** マップの節の種類 */
  type MapNodeKind = "target" | "category" | "phase" | "item";

  /** マップの節（ELK に渡し、配置された座標が入って戻る） */
  export type MapNode = {
    id: string;
    width: number;
    height: number;
    kind: MapNodeKind;
    label: string;
    item?: Item;
    x?: number;
    y?: number;
  };

  /** マップの枝（ELK に渡し、配置された経路が入って戻る） */
  export type MapEdge = {
    id: string;
    sources: string[];
    targets: string[];
    sections?: {
      startPoint: { x: number; y: number };
      endPoint: { x: number; y: number };
      bendPoints?: { x: number; y: number }[];
    }[];
  };

  /** ELK に渡すグラフ（配置の後は `width`・`height` が入る） */
  export type MapGraph = {
    id: string;
    layoutOptions: Record<string, string>;
    children: MapNode[];
    edges: MapEdge[];
    width?: number;
    height?: number;
  };

  /** 節の種類ごとの大きさ（幅・高さ） */
  const NODE_SIZE: Record<MapNodeKind, [number, number]> = {
    target: [130, 40],
    category: [150, 34],
    phase: [118, 26],
    item: [268, 48],
  };

  /** 設定に無い対象・カテゴリー・フェーズに付ける名前 */
  const UNSET = "（未設定）";

  /** 木を左から右へ、直角の枝で並べる ELK の設定 */
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

  /** 拡大・縮小 1 回の倍率の幅と、倍率の範囲 */
  const ZOOM_STEP = 0.15;
  const ZOOM_MIN = 0.4;
  const ZOOM_MAX = 1.5;

  /** ホイール 1 回の倍率の掛け率（図の拡大と同じ刻み） */
  const WHEEL_FACTOR = 1.12;

  /** マップの狭い幅の境（これ以下は字下げした縦の一覧） */
  const NARROW_QUERY = "(max-width: 900px)";

  /** 絞り込みの条件に合う検討事項が 1 件も無いときに、マップの枠と字下げの一覧に出す文 */
  const NO_SHOWN_DECISIONS_TEXT = "表示する検討事項はありません。";

  /** 対象 → カテゴリー → フェーズ → 検討事項の木を、渡した検討事項だけで組んで返す（ELK に渡す節と枝の形） */
  export function buildDecisionTree({
    index,
    decisions,
  }: {
    index: RecordIndex;
    /** 絞り込みの条件に合う検討事項 */
    decisions: Item[];
  }): MapGraph {
    const { settings } = index.data;
    const shown = [...decisions].sort((a, b) => compareIds(a.id, b.id));
    /** 設定の並びの順（設定に無いものは最後） */
    const rankIn = (list: string[], name: string): number => {
      const position = list.indexOf(name);
      return position < 0 ? list.length : position;
    };
    const targetOf = (item: Item): string =>
      settings.categories.find((category) => category.name === item.category)?.target ??
      item.target ??
      UNSET;
    const categoryOf = (item: Item): string => item.category ?? UNSET;
    const phaseOf = (item: Item): string => item.phase ?? UNSET;
    const unique = (values: string[]): string[] => [...new Set(values)];

    const children: MapNode[] = [];
    const edges: MapEdge[] = [];
    const add = (id: string, kind: MapNodeKind, label: string, parent: string | null, item?: Item) => {
      const [width, height] = NODE_SIZE[kind];
      children.push({ id, width, height, kind, label, item });
      if (parent !== null) edges.push({ id: `${parent}>${id}`, sources: [parent], targets: [id] });
    };
    const targets = unique(shown.map(targetOf)).sort(
      (a, b) =>
        rankIn(
          settings.targets.map((target) => target.name),
          a,
        ) -
        rankIn(
          settings.targets.map((target) => target.name),
          b,
        ),
    );
    for (const target of targets) {
      const targetId = `target:${target}`;
      add(targetId, "target", target, null);
      const ofTarget = shown.filter((item) => targetOf(item) === target);
      const categories = unique(ofTarget.map(categoryOf)).sort(
        (a, b) =>
          rankIn(
            settings.categories.map((category) => category.name),
            a,
          ) -
          rankIn(
            settings.categories.map((category) => category.name),
            b,
          ),
      );
      for (const category of categories) {
        const categoryId = `category:${target}/${category}`;
        add(categoryId, "category", category, targetId);
        const ofCategory = ofTarget.filter((item) => categoryOf(item) === category);
        const phases = unique(ofCategory.map(phaseOf)).sort(
          (a, b) => rankIn(settings.phases, a) - rankIn(settings.phases, b),
        );
        for (const phase of phases) {
          const phaseId = `phase:${target}/${category}/${phase}`;
          add(phaseId, "phase", phase, categoryId);
          for (const item of ofCategory.filter((candidate) => phaseOf(candidate) === phase)) {
            add(item.id, "item", item.title, phaseId, item);
          }
        }
      }
    }
    return { id: "graph", layoutOptions: ELK_OPTIONS, children, edges };
  }

  // ───── マップの状態（描き直しても保つ） ─────

  /** マップの状態 */
  const mapState: {
    keyword: string;
    zoom: number | "fit";
    scroll: { left: number; top: number } | null;
    selected: string | null;
    /** 前に押した節（素早い 2 回目を、描き直しで節が消えた位置を押しても、前に押した節への 2 回押しとして扱う） */
    lastPress: Press | null;
  } = {
    keyword: "",
    zoom: "fit",
    scroll: null,
    selected: null,
    lastPress: null,
  };

  /** 配置の結果（絞り込みの条件に合う検討事項の組み合わせごと） */
  const layoutCache = new Map<string, MapGraph>();

  /** 配置を計算する（同じ状態の組み合わせは取っておく） */
  async function layoutOf(graph: MapGraph, key: string): Promise<MapGraph> {
    const cached = layoutCache.get(key);
    if (cached !== undefined) return cached;
    const laid = (await new ELK().layout(graph as never)) as unknown as MapGraph;
    layoutCache.set(key, laid);
    return laid;
  }

  /** 前提 → 後続の線の道筋（同じ列どうしは、節の右側にふくらむ弧でつなぐ） */
  function dependencyPath(from: MapNode, to: MapNode): string {
    const fromX = (from.x ?? 0) + from.width;
    const fromY = (from.y ?? 0) + from.height / 2;
    // 同じ列
    if (Math.abs((from.x ?? 0) - (to.x ?? 0)) < 10) {
      const toY = (to.y ?? 0) + to.height / 2;
      const bulge = 28 + Math.min(60, Math.abs(toY - fromY) / 6);
      return `M${fromX},${fromY} C${fromX + bulge},${fromY} ${fromX + bulge},${toY} ${fromX},${toY}`;
    }
    const toX = to.x ?? 0;
    const toY = (to.y ?? 0) + to.height / 2;
    const reach = Math.max(60, Math.abs(toX - fromX) / 2);
    return `M${fromX},${fromY} C${fromX + reach},${fromY} ${toX - reach},${toY} ${toX},${toY}`;
  }

  /** SVG の要素を作る */
  function svg<K extends keyof SVGElementTagNameMap>(
    tag: K,
    attrs: Record<string, string>,
  ): SVGElementTagNameMap[K] {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attrs)) element.setAttribute(name, value);
    return element;
  }

  /** 木の節と枝を、配置された座標で描く。注目の起点（ロックした節、ロックしていなければ詳細を開いている節）の根までの枝と依存の線を強調し、ほかを薄くする */
  function drawMap({
    laid,
    canvas,
    selected,
    lockedId,
    press,
    marks,
    comments,
  }: {
    laid: MapGraph;
    canvas: HTMLElement;
    /** 詳細パネルで開いている項目 */
    selected: string | null;
    /** 効いているロック（絞り込みで描いていなければ null） */
    lockedId: string | null;
    /** 節を押した（押した節の ID と、押したイベント） */
    press: (id: string, event: MouseEvent) => void;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks | undefined;
    /** 項目の ID → レビュー中のコメントの件数。渡したとき、節点の 2 行目の右端に印を置く場所を置く */
    comments?: Record<string, number> | undefined;
  }): void {
    const positions = new Map(laid.children.map((node) => [node.id, node]));
    const parentOf = new Map(laid.edges.map((edge) => [edge.targets[0], edge.sources[0]]));
    // 強調の起点はロックした節。ロックしていなければ、詳細を開いている節
    const opened = selected;
    const lockedHere = lockedId !== null && positions.has(lockedId);
    if (lockedHere) selected = lockedId;
    // 選んだ項目から根までの節
    const chain = new Set<string>();
    for (let id = selected; id !== null && id !== undefined; id = parentOf.get(id) ?? null) chain.add(id);

    const edgeSvg = svg("svg", {
      class: "edges",
      width: String(laid.width ?? 0),
      height: String(laid.height ?? 0),
      "aria-hidden": "true",
    });
    for (const edge of laid.edges) {
      const section = edge.sections?.[0];
      if (section === undefined) continue;
      const points = [section.startPoint, ...(section.bendPoints ?? []), section.endPoint];
      const [source, target] = [edge.sources[0], edge.targets[0]];
      edgeSvg.append(
        svg("path", {
          class: `edge-tree${chain.has(source) && chain.has(target) ? " rel" : ""}`,
          d: `M${points.map((point) => `${point.x},${point.y}`).join(" L")}`,
        }),
      );
    }
    // 依存の線: 前提 → 後続。選んだ項目に関わる線を強め、その上を小さな玉が流れる
    const near = new Set(chain);
    let flowId = 0;
    for (const node of laid.children) {
      if (node.kind !== "item" || node.item === undefined) continue;
      for (const prerequisite of node.item.depends_on ?? []) {
        const from = positions.get(prerequisite);
        if (from === undefined) continue;
        const related = selected !== null && (selected === prerequisite || selected === node.id);
        const id = `dep-${(flowId += 1)}`;
        edgeSvg.append(
          svg("path", { id, class: `edge-dep${related ? " rel" : ""}`, d: dependencyPath(from, node) }),
        );
        if (related) {
          near.add(prerequisite);
          near.add(node.id);
          // 選んだ項目から外へ向かって、玉をゆっくり流す（入ってくる線は向きを逆にする）
          const incoming = node.id === selected;
          for (const begin of [0, 1.6]) {
            const dot = svg("circle", { class: "flow-dot", r: "2.6" });
            const motion = svg("animateMotion", {
              dur: "3.2s",
              begin: `${begin}s`,
              repeatCount: "indefinite",
              ...(incoming ? { keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" } : {}),
            });
            motion.append(svg("mpath", { href: `#${id}` }));
            dot.append(motion);
            edgeSvg.append(dot);
          }
        }
      }
    }
    const keyword = mapState.keyword.toLowerCase();
    const nodes = laid.children.map((node) => {
      const style = `left:${node.x ?? 0}px;top:${node.y ?? 0}px;width:${node.width}px;height:${node.height}px`;
      const rel = near.has(node.id) ? " rel" : "";
      if (node.kind !== "item" || node.item === undefined) {
        return h({
          tag: "div",
          attrs: { class: `map-node n-${node.kind}${rel}`, "data-node": node.id, style },
          children: [h({ tag: "span", attrs: { class: "lbl" }, children: [node.label] })],
        });
      }
      const item = node.item;
      const hit = keyword !== "" && item.title.toLowerCase().includes(keyword);
      return h({
        tag: "button",
        attrs: {
          class: `map-node n-item${opened === item.id ? " sel" : ""}${lockedHere && lockedId === item.id ? " locked" : ""}${hit ? " hit" : ""}${rel}`,
          type: "button",
          "data-node": item.id,
          style,
          title: `${item.title}（${item.status ?? ""}）`,
          onclick: (event: Event) => press(item.id, event as MouseEvent),
        },
        children: [
          // 鍵は節の右上の内側に置く。開いた鍵は詳細を開いている節にカーソルを乗せたときだけ、閉じた鍵はロック中いつも出す（出し分けは CSS）
          h({
            tag: "span",
            attrs: { class: "lk", "aria-hidden": "true" },
            children: [icon(lockedHere && lockedId === item.id ? "lock" : "unlock")],
          }),
          h({
            tag: "span",
            attrs: { class: "r1" },
            children: [
              statusMark(item.status),
              h({ tag: "span", attrs: { class: "lbl" }, children: [item.title] }),
            ],
          }),
          h({
            tag: "span",
            attrs: { class: "r2" },
            children: [
              markFor({ marks, id: item.id }),
              h({ tag: "span", attrs: { class: "mono" }, children: [item.id] }),
              h({ tag: "span", children: [item.status ?? ""] }),
              item.weight === undefined ? null : h({ tag: "span", children: [`影響度 ${item.weight}`] }),
              comments === undefined ? null : commentPlace({ id: item.id, count: comments[item.id] }),
            ],
          }),
        ],
      });
    });
    canvas.classList.toggle("focusing", selected !== null);
    // ロック中は、開いた鍵を出さない
    canvas.classList.toggle("has-lock", lockedHere);
    canvas.style.width = `${laid.width ?? 0}px`;
    canvas.style.height = `${laid.height ?? 0}px`;
    canvas.replaceChildren(edgeSvg, ...nodes);
  }

  /** 狭い幅で使う、字下げした縦の一覧 */
  function outline({
    index,
    decisions,
    open,
    marks,
    comments,
  }: {
    index: RecordIndex;
    /** 絞り込みの条件に合う検討事項 */
    decisions: Item[];
    open: (id: string) => void;
    /** 項目の ID → 差分の印。差分の表示の間だけ渡す */
    marks?: DiffMarks | undefined;
    /** 項目の ID → レビュー中のコメントの件数。渡したとき、タイトルと差分の印の右に印を置く場所を置く */
    comments?: Record<string, number> | undefined;
  }): HTMLElement {
    const tree = buildDecisionTree({ index, decisions });
    const nodeOf = new Map(tree.children.map((node) => [node.id, node]));
    const childrenOf = new Map<string, MapNode[]>();
    for (const edge of tree.edges) {
      const list = childrenOf.get(edge.sources[0]) ?? [];
      const child = nodeOf.get(edge.targets[0]);
      if (child !== undefined) list.push(child);
      childrenOf.set(edge.sources[0], list);
    }
    /** 節と、その下の節を字下げして並べる */
    const entry = (node: MapNode): HTMLElement => {
      const label =
        node.kind === "item" && node.item !== undefined
          ? h({
            tag: "button",
            attrs: { type: "button", "data-id": node.id, onclick: () => open(node.id) },
            children: [
              statusMark(node.item.status),
              h({ tag: "span", children: [node.label] }),
              markFor({ marks, id: node.id }),
              comments === undefined ? null : commentPlace({ id: node.id, count: comments[node.id] }),
            ],
          })
          : h({ tag: "div", attrs: { class: `o-${node.kind}` }, children: [node.label] });
      const below = childrenOf.get(node.id) ?? [];
      return h({
        tag: "li",
        children: [
          label,
          below.length > 0 ? h({ tag: "ul", children: [...below.map(entry)] }) : null,
        ],
      });
    };
    const roots = tree.children.filter((node) => node.kind === "target");
    return h({
      tag: "nav",
      attrs: { class: "map-outline", "aria-label": "検討事項の一覧" },
      // 絞り込みの条件に合う検討事項が無いときは、対象の見出しを並べず空の旨を出す
      children: [roots.length > 0 ? h({ tag: "ul", children: [...roots.map(entry)] }) : emptyNote(NO_SHOWN_DECISIONS_TEXT)],
    });
  }

  /** ホイール 1 回で変えた後のマップの倍率と、マウスの下の点を残す枠のスクロールの位置を返す */
  export function wheelZoom({
    scale,
    deltaY,
    point,
    scroll,
  }: {
    /** 今当たっている倍率 */
    scale: number;
    /** `wheel` の `deltaY`（符号だけを見る） */
    deltaY: number;
    /** マウスの位置（枠の左上からの px） */
    point: { x: number; y: number };
    /** 枠の今のスクロールの位置 */
    scroll: { left: number; top: number };
  }): { scale: number; scroll: { left: number; top: number } } {
    // 奥へ回すと拡大、手前へ回すと縮小。下限は、全体を表示の倍率が ZOOM_MIN を下回っているときにその倍率で止める
    const factor = deltaY < 0 ? WHEEL_FACTOR : 1 / WHEEL_FACTOR;
    const next = Math.min(ZOOM_MAX, Math.max(Math.min(ZOOM_MIN, scale), scale * factor));
    // マウスの下の点が、倍率を変えた後も同じ位置に残るようにスクロールの位置を求める
    const ratio = next / scale;
    return {
      scale: next,
      scroll: {
        left: (scroll.left + point.x) * ratio - point.x,
        top: (scroll.top + point.y) * ratio - point.y,
      },
    };
  }

  /** 検討事項の画面が受ける操作（項目を開く・表示形式を切り替えるに、マップの余白で選びを外すを足す） */
  export type DecisionsScreenProps = Omit<ScreenProps, "on"> & {
    on: ScreenProps["on"] & {
      /** 選びを外す（詳細パネルの「閉じる」と同じ） */
      clear: () => void;
      /** マップの節か余白を押した（押した節の ID か `null`）。入口が `lockTap` で判定して `LockAction` を返す */
      lock: (id: string | null) => LockAction;
    };
    /** 効いているロック（入口の `LockState.map` の検討事項を描いていればその ID、絞り込みで描いていなければ `null`）。マップの節に閉じた鍵を出す */
    lockedId: string | null;
  };

  /** マップの道具の行（表示形式・キーワード）と、マップの枠・拡大の道具・絞り込みのドロワーを作る */
  function mapView(
    { index, route, on, marks, comments, lockedId }: DecisionsScreenProps,
    {
      shown,
      chips,
      makeDrawer,
    }: {
      /** 絞り込みの条件に合う検討事項 */
      shown: Item[];
      /** 条件のチップの行（値を選んでいる条件が無ければ null） */
      chips: HTMLElement | null;
      /** ドロワーを組む（開いていなければ null。キーワードに一致した件数を添えるには `hit` を渡す） */
      makeDrawer: (hit?: (row: Row) => boolean) => HTMLDialogElement | null;
    },
  ): HTMLElement {
    const root = h({ tag: "div", attrs: { class: "map-view-root" } });
    const frame = h({ tag: "div", attrs: { class: "map-frame" } });
    // 絞り込みの条件に合う検討事項が無いときに、マップの枠の中央に出す文
    const emptyNotice = h({ tag: "p", attrs: { class: "empty map-empty", hidden: true }, children: [NO_SHOWN_DECISIONS_TEXT] });
    const canvas = h({ tag: "div", attrs: { id: "decision-map", class: "map-canvas", role: "group", "aria-label": "検討事項のマップ" } });
    const sizer = h({ tag: "div", attrs: { class: "map-sizer" }, children: [canvas] });
    const wrap = h({ tag: "div", attrs: { class: "map-wrap" }, children: [sizer] });
    // 全体を表示のボタン（押された状態を見た目に出す）
    const fitButton = h({
      tag: "button",
      attrs: {
        class: "btn ghost",
        type: "button",
        "aria-pressed": "false",
        onclick: () => {
          mapState.zoom = mapState.zoom === "fit" ? 1 : "fit";
          applyZoom();
        },
      },
      children: ["全体を表示"],
    });
    let outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments });
    let current: MapGraph | null = null;
    /** キーワードに当たった検討事項か */
    const isHit = (item: Item): boolean =>
      mapState.keyword !== "" && item.title.toLowerCase().includes(mapState.keyword.toLowerCase());
    /** 絞り込みのドロワー（キーワードに一致した件数を値ごとに添える） */
    const drawerHit = (row: Row): boolean => isHit(row as Item);
    let drawerElement = makeDrawer(drawerHit);
    /** キーワードが変わったとき、ドロワーの件数だけを組み直す */
    const refreshDrawer = (): void => {
      if (drawerElement === null) return;
      const next = makeDrawer(drawerHit);
      if (next === null) return;
      drawerElement.replaceWith(next);
      drawerElement = next;
    };

    /** 拡大率を決めて、マップの大きさと拡大を当てる（全体を表示は、枠に木の全体が収まる倍率） */
    const applyZoom = (): void => {
      if (current === null) return;
      const width = current.width ?? 0;
      const height = current.height ?? 0;
      const scale =
        mapState.zoom === "fit"
          ? Math.min(1, (wrap.clientWidth - 16) / width, (wrap.clientHeight - 16) / height)
          : mapState.zoom;
      // 全体を表示は右と下に決まった余白、数値の倍率は枠の幅・高さの分の余白（マップが枠より小さくても、ホイールで拡大した点を残せるだけ送れる）
      const marginRight = mapState.zoom === "fit" ? 240 : wrap.clientWidth;
      const marginBottom = mapState.zoom === "fit" ? 160 : wrap.clientHeight;
      sizer.style.width = `${width * scale + marginRight}px`;
      sizer.style.height = `${height * scale + marginBottom}px`;
      canvas.style.transform = `scale(${scale})`;
      fitButton.setAttribute("aria-pressed", String(mapState.zoom === "fit"));
    };

    /** 今当たっているマップの倍率（全体を表示は、求めて当てた倍率） */
    const shownScale = (): number =>
      mapState.zoom === "fit" ? Number.parseFloat(canvas.style.transform.slice(6)) : mapState.zoom;

    /** 効いているロック（幅 900px 以下では詳細が全面に出るので、ロックしない） */
    const lockedNow = (): string | null => (matchMedia(LOCK_QUERY).matches ? lockedId : null);

    /** ロックした節の鍵（描き直しても今の要素を引く） */
    const lockedKey = (): HTMLElement | null => canvas.querySelector<HTMLElement>(".n-item.locked .lk");

    /** 節（余白なら `null`）を押した。素早い 2 回目は、描き直しで節が消えた位置でも前に押した節への 2 回押しとして、ネットワークと同じ規則で入口へ渡す */
    const press = (hit: string | null, event: { clientX: number; clientY: number }): void => {
      // 幅 900px 以下の字下げの一覧ではロックせず、節を開く
      if (!matchMedia(LOCK_QUERY).matches) {
        if (hit !== null) on.open(hit);
        return;
      }
      const pressInfo: Press = { time: performance.now(), x: event.clientX, y: event.clientY, id: hit };
      const pressed = resolvePress({ last: mapState.lastPress, press: pressInfo });
      mapState.lastPress = pressInfo;
      if (on.lock(pressed) === "shake") shakeKeyElement(lockedKey);
    };

    /** 配置を求めて、マップを描く。注目の起点（ロックした節、ロックしていなければ詳細を開いている節）が変わってその節があるときは、その節が中央に来るようにマップを送り、それ以外は描き直す前のスクロールの位置へ戻す */
    const draw = async (): Promise<void> => {
      outlineElement.replaceWith((outlineElement = outline({ index, decisions: shown, open: on.open, marks, comments })));
      if (missingLibraries(["elkjs"]).length > 0) return;
      const key = shown.map((item) => item.id).join(",");
      const graph = buildDecisionTree({ index, decisions: shown });
      emptyNotice.hidden = graph.children.length > 0;
      current = await layoutOf(graph, key);
      drawMap({ laid: current, canvas, selected: route.id, lockedId: lockedNow(), press, marks, comments });
      applyZoom();
      // 中央へ送る節は、ロックした節。ロックしていなければ詳細を開いている節（ロック中にほかの節を開いても送り直さない）
      const locked = lockedNow();
      const anchorId = locked !== null && current.children.some((n) => n.id === locked) ? locked : route.id;
      const node = anchorId === null ? undefined : current.children.find((n) => n.id === anchorId);
      const scale = shownScale();
      if (node !== undefined && anchorId !== mapState.selected) {
        wrap.scrollTo({
          left: ((node.x ?? 0) + node.width / 2) * scale - wrap.clientWidth / 2,
          top: ((node.y ?? 0) + node.height / 2) * scale - wrap.clientHeight / 2,
        });
      } else if (mapState.scroll !== null) {
        wrap.scrollTo(mapState.scroll);
      }
      mapState.selected = anchorId;
    };

    // ===== 道具の行 =====
    const keyword = h({
      tag: "input",
      attrs: {
        class: "input map-q",
        type: "search",
        placeholder: "タイトルで強調",
        value: mapState.keyword,
        "aria-label": "タイトルで強調するキーワード",
      },
    });
    let timer: number | undefined;
    keyword.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        mapState.keyword = keyword.value;
        // 当たった節の色と、ドロワーの一致した件数だけを更新する
        for (const button of canvas.querySelectorAll<HTMLElement>("button.n-item")) {
          const item = index.byId.get(button.dataset["node"] ?? "")?.item;
          button.classList.toggle("hit", item !== undefined && isHit(item));
        }
        refreshDrawer();
      }, 150);
    });
    const toolbarElement = toolbar(
      [
        { key: "board", label: "ボード" },
        { key: "map", label: "マップ" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
    );
    toolbarElement.append(keyword);

    /** 拡大・縮小・全体を表示のボタン（マップの枠の外に置く） */
    const zoomBar = h({
      tag: "div",
      attrs: { class: "zoom", role: "group", "aria-label": "拡大率" },
      children: [
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": "縮小",
            onclick: () => {
              const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
              mapState.zoom = Math.max(ZOOM_MIN, Math.round((base - ZOOM_STEP) * 100) / 100);
              applyZoom();
            },
          },
          children: ["−"],
        }),
        fitButton,
        h({
          tag: "button",
          attrs: {
            class: "icon-btn",
            type: "button",
            "aria-label": "拡大",
            onclick: () => {
              const base = mapState.zoom === "fit" ? 0.6 : mapState.zoom;
              mapState.zoom = Math.min(ZOOM_MAX, Math.round((base + ZOOM_STEP) * 100) / 100);
              applyZoom();
            },
          },
          children: ["＋"],
        }),
      ],
    });
    wrap.addEventListener("scroll", () => {
      mapState.scroll = { left: wrap.scrollLeft, top: wrap.scrollTop };
    });
    // ホイールで拡大・縮小する（ページを動かさないよう既定の動作を止め、マウスの下の点を残す）
    wrap.addEventListener(
      "wheel",
      (event) => {
        // 横にだけ回したときは、枠の横スクロールに任せる
        if (event.deltaY === 0) return;
        event.preventDefault();
        // マップを描く前は、倍率が無い
        if (current === null) return;
        const box = wrap.getBoundingClientRect();
        const next = wheelZoom({
          scale: shownScale(),
          deltaY: event.deltaY,
          point: { x: event.clientX - box.left - wrap.clientLeft, y: event.clientY - box.top - wrap.clientTop },
          scroll: { left: wrap.scrollLeft, top: wrap.scrollTop },
        });
        // 数値の倍率にして（「全体を表示」の押された状態を外す）、スクロールの位置を当てる
        mapState.zoom = next.scale;
        applyZoom();
        wrap.scrollTo(next.scroll);
      },
      { passive: false },
    );
    // 余白を押したとき: 押した節が描き直しで消えた位置への素早い 2 回目は、その節への 2 回押しとして扱う。ロックの規則で、全体の表示へ戻す（`blank`）か鍵を震わせる
    enableDragScroll(wrap, (event) => press(null, event));

    // elkjs が読めない: 知らせを出し、表示形式を表に切り替えると読めることを伝える
    const notice =
      missingLibraries(["elkjs"]).length > 0
        ? h({
          tag: "div",
          children: [
            libraryNotice({ names: ["elkjs"], what: "マップ" }),
            emptyNote("表示形式を「表」に切り替えると、検討事項を表示できます。"),
          ],
        })
        : null;
    frame.append(emptyNotice, wrap);
    if (notice !== null) frame.hidden = true;

    append({
      parent: root,
      children: [
        toolbarElement,
        chips,
        notice,
        frame,
        zoomBar,
        outlineElement,
        drawerElement,
      ],
    });
    // 拡大率が「全体を表示」のときは、枠の大きさが変わるたびに倍率を求め直す
    new ResizeObserver(() => {
      if (mapState.zoom === "fit") applyZoom();
    }).observe(wrap);
    void draw();
    return root;
  }

  /** 検討事項の表の列（`filterable` の列が絞り込みのドロワーの条件になる） */
  function decisionColumns({ index, open }: { index: RecordIndex; open: (id: string) => void }): Column[] {
    const common = commonColumns(index.data.settings);
    return [
      common.id,
      common.title(),
      common.status(DECISION_STATUSES),
      common.target,
      common.category,
      common.phase,
      {
        key: "weight",
        label: "影響度",
        nowrap: true,
        filterable: true,
        order: ["大", "中", "小"],
        priority: 3,
        get: (row) => (typeof row["weight"] === "string" ? row["weight"] : undefined),
        cell: (row) => impactBadge(typeof row["weight"] === "string" ? row["weight"] : undefined),
      },
      {
        key: "ready",
        label: "着手可否",
        nowrap: true,
        filterable: true,
        order: ["着手可能", "前提待ち", "なし"],
        priority: 2,
        // 前提が全て決着した未決定（build が計算した次の候補）は着手可能、ほかの未決定は前提待ち、未決定以外はなし
        get: (row) => (row.status !== "未決定" ? "なし" : index.readyIds.has(row.id) ? "着手可能" : "前提待ち"),
      },
      {
        key: "depends_on",
        label: "前提",
        priority: 3,
        get: (row) => rowTexts(row, "depends_on"),
        cell: (row) => idLinksCell(rowTexts(row, "depends_on"), open),
      },
      common.tags,
    ];
  }

  /** 絞り込みの条件に合う検討事項の ID（マップが描く節。ロックした節を描いているかの判定にも使う） */
  export function shownDecisionIds({ index, filters }: { index: RecordIndex; filters: Filters }): Set<string> {
    const columns = decisionColumns({ index, open: () => undefined });
    return new Set(filterRows({ rows: index.data.decisions, columns, filters }).map((row) => row.id));
  }

  /** 検討事項の画面を返す */
  export function decisionsScreen(props: DecisionsScreenProps): HTMLElement {
    const { index, route, on, marks, comments, filters, drawerOpen } = props;
    const columns = decisionColumns({ index, open: on.open });
    // 絞り込みの条件に合う検討事項を、マップ・ボード・表に同じ結果で渡す
    const shown = filterRows({ rows: index.data.decisions, columns, filters }) as Item[];
    // 表以外の表示形式では、ツールバーの下に条件のチップの行を置く
    const chips =
      activeConditionCount(filters) > 0
        ? filterChips({
            filters,
            labels: Object.fromEntries(columns.map((column) => [column.key, column.label])),
            onFilter: on.filter,
          })
        : null;
    const makeDrawer = (hit?: (row: Row) => boolean): HTMLDialogElement | null =>
      screenDrawer({
        drawerOpen,
        rows: index.data.decisions,
        columns: columns.filter((column) => column.filterable === true),
        textColumns: textColumns(columns),
        filters,
        shown: shown.length,
        hit,
        onFilter: on.filter,
        onClose: on.closeDrawer,
      });
    if (route.view === "map") {
      return h({
        tag: "div",
        attrs: { class: "screen decisions" },
        children: [mapView(props, { shown, chips, makeDrawer })],
      });
    }
    const toolbarElement = toolbar(
      [
        { key: "board", label: "ボード" },
        { key: "map", label: "マップ" },
        { key: "table", label: "表" },
      ],
      route,
      on.view,
    );
    if (route.view === "board") {
      return h({
        tag: "div",
        attrs: { class: "screen decisions" },
        children: [
          toolbarElement,
          chips,
          board({
            columns: boardColumns({
              items: shown,
              statuses: [...DECISION_STATUSES],
              statusFilter: filters["status"] ?? [],
            }),
            card: (item) =>
              boardCard({
                index,
                item,
                meta: [item.category, item.phase],
                links: item.depends_on ?? [],
                open: on.open,
                mark: marks?.[item.id],
                comments,
              }),
            emptyText: "検討事項はありません。",
          }),
          makeDrawer(),
        ],
      });
    }
    return h({
      tag: "div",
      attrs: { class: "screen decisions" },
      children: [
        toolbarElement,
        managedTable({
          kind: "decisions",
          columns,
          rows: shown,
          filters,
          onFilter: on.filter,
          open: on.open,
          marks,
          ...(comments === undefined ? {} : { comments }),
        }),
        makeDrawer(),
      ],
    });
  }
}
