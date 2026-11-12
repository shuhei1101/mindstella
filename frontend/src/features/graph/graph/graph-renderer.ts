// ネットワークの描画（今の画面の `graph/graph.ts` の視点・操作・毎コマの描画と同じ値）。React に依存せず、`GraphCanvas` が差し替えの関数で同期する
import { createElement, type ReactElement } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";

import type { Graph, GraphLink, GraphNode, LinkType } from "@/features/graph/graph/graph-model";
import { bakeGlow, drawLook, FOCAL, hashUnit, LABEL_LIFT, lookLabelColor, type LookFrame, type LookLink, type LookStar, type Vec3 } from "@/features/graph/graph/looks";
import { CommentMark } from "@/shared/components/comment-mark";
import { Icon, StatusMark } from "@/shared/components/icon";
import { LOCK_QUERY, resolvePress, SHAKE_GROW, SHAKE_MS, SHAKE_SHIFT, SHAKE_SWING, shakeAt, shakeColor, type Press } from "@/shared/core/lock";
import type { Item, Kind, NetworkLook, RecordIndex } from "@/shared/core/records";

/** 描画を差し替える関数の組 */
export type GraphRenderer = {
  /** 玉と線を作り直す（名前・状態の印は索引から引く。視点は全体が収まる向きと距離に戻す） */
  setGraph: (input: { graph: Graph; index: RecordIndex }) => void;
  /** 次のコマからその見た目で描く */
  setLook: (look: NetworkLook) => void;
  /** 次のコマからそのライト / ダークで描く */
  setTheme: (theme: "light" | "dark") => void;
  /** 注目の起点（ロック、無ければ詳細の項目）へ寄る */
  setFocus: (focus: { selectedId: string | null; lockedId: string | null }) => void;
  /** 名前の横のコメントの印の件数を差し替える */
  setComments: (counts: Record<string, number>) => void;
  /** 閉じた鍵の震えを今から始める */
  shake: () => void;
  /** 毎コマの描画とリスナーを外す */
  destroy: () => void;
};

/** 力で整えた玉 */
type Ball = GraphNode &
  Vec3 & {
    title: string;
    label: string;
    /** つながる線の数 */
    degree: number;
    /** 玉の半径（つながりの数で変わる） */
    radius: number;
    /** 力で整えた位置（注目が外れたら戻る） */
    home: Vec3;
    /** 注目していない玉を沈める度合い（1 が通常） */
    fade: number;
    /** またたきの位相（0〜1） */
    seed: number;
  };

/** 項目の種類 → 色のトークン */
const KIND_COLOR_VAR: Record<Kind, string> = {
  decisions: "--k-dec",
  tasks: "--k-task",
  research: "--k-res",
  docs: "--k-doc",
  terms: "--k-term",
  notes: "--k-note",
  logs: "--k-log",
};

/** メディアクエリ（持たない環境では当たらないものとして扱う） */
const media = (query: string): { matches: boolean } => (typeof window.matchMedia === "function" ? window.matchMedia(query) : { matches: false });

/** React の部品を 1 度だけ描いた要素にする（毎コマ描き直さない絵・印に使う） */
const staticElement = (node: ReactElement): HTMLElement => {
  const host = document.createElement("div");
  const root = createRoot(host);
  flushSync(() => {
    root.render(node);
  });
  const element = host.firstElementChild as HTMLElement;
  root.unmount();
  host.append(element);
  element.remove();
  return element;
};

/** 文字の書体（太さつき）。倍率は描くときにかけるので、10px で持つ */
const FONT_NORMAL = '400 10px "JetBrains Mono", "Noto Sans JP", monospace';
const FONT_BOLD = '500 10px "JetBrains Mono", "Noto Sans JP", monospace';

/** 玉の上の文字を画像に描くときの、元の大きさに対する倍率 */
const LABEL_RESOLUTION = 4;

/** 文字の画像の高さ（10px の文字に対する px） */
const LABEL_HEIGHT = 14;

/** 寄せる先: 乗せた玉との距離の 1 割だけ近づいたところ（残す割合） */
const PULL_KEEP = 0.9;

/** 毎コマ、目標へ寄せる割合 */
const PULL_EASE = 0.03;

/** 操作が止まってから自動で回り始めるまでの時間（ms） */
const IDLE_BEFORE_ROTATE_MS = 2500;

/** 自動の回転の速さ（毎コマの角度） */
const AUTO_ROTATE_STEP = 0.00018;

/** 項目の種類ごとの玉の色など、テーマで変わる色 */
type GraphColors = {
  kind: Record<Kind, string>;
  label: string;
  line: string;
  dot: string;
  ring: string;
};

/** 色をトークンから引く */
const readColors = (): GraphColors => {
  const style = getComputedStyle(document.documentElement);
  const read = (name: string): string => style.getPropertyValue(name).trim();
  return {
    kind: Object.fromEntries(
      Object.entries(KIND_COLOR_VAR).map(([kind, name]) => [kind, read(name)]),
    ) as Record<Kind, string>,
    label: read("--g-label"),
    line: read("--g-line"),
    dot: read("--g-dot"),
    ring: read("--accent"),
  };
}

/** 玉を球面上に黄金角の螺旋で散らして置き、線の数から半径を決める */
const placeBalls = (index: RecordIndex, graph: { nodes: GraphNode[]; links: GraphLink[] }): Ball[] => {
  const balls: Ball[] = graph.nodes.map((node, position, all) => {
    const t = (position + 0.5) / all.length;
    const phi = Math.acos(1 - 2 * t);
    const theta = Math.PI * (1 + Math.sqrt(5)) * position;
    const title = index.byId.get(node.id)?.item.title ?? node.id;
    const x = 120 * Math.sin(phi) * Math.cos(theta);
    const y = 120 * Math.cos(phi);
    const z = 120 * Math.sin(phi) * Math.sin(theta);
    return {
      ...node,
      x,
      y,
      z,
      title,
      label: title.length > 22 ? `${title.slice(0, 21)}…` : title,
      degree: 0,
      radius: 4,
      home: { x, y, z },
      fade: 1,
      seed: hashUnit(node.id),
    };
  });
  const byId = new Map(balls.map((ball) => [ball.id, ball]));
  for (const link of graph.links) {
    const from = byId.get(link.source);
    const to = byId.get(link.target);
    if (from !== undefined) from.degree += 1;
    if (to !== undefined) to.degree += 1;
  }
  for (const ball of balls) ball.radius = 4 + Math.sqrt(ball.degree) * 2.2;
  return balls;
};

/** 互いに離れ、線でつながったものは引き合い、中心へ寄る力を、玉が落ち着くまで繰り返して位置を整える */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ描き方を 1 か所で読めるように保つ
const settle = (balls: Ball[], links: { s: Ball; t: Ball; type: LinkType }[]): void => {
  // 玉が多いほど繰り返しを減らす（総当たりの計算が増えるため）
  const steps = Math.max(40, Math.min(260, Math.floor(120000 / Math.max(1, balls.length))));
  const velocity = new Map(balls.map((ball) => [ball.id, { x: 0, y: 0, z: 0 }]));
  let alpha = 1;
  for (let step = 0; step < steps; step += 1) {
    for (let i = 0; i < balls.length; i += 1) {
      for (let j = i + 1; j < balls.length; j += 1) {
        const a = balls[i];
        const b = balls[j];
        if (a === undefined || b === undefined) continue;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dz = a.z - b.z;
        const force = (4400 / (dx * dx + dy * dy + dz * dz + 1)) * alpha;
        const va = velocity.get(a.id) as Vec3;
        const vb = velocity.get(b.id) as Vec3;
        va.x += dx * force;
        va.y += dy * force;
        va.z += dz * force;
        vb.x -= dx * force;
        vb.y -= dy * force;
        vb.z -= dz * force;
      }
    }
    for (const link of links) {
      const want = link.type === "depends" ? 84 : link.type === "related" ? 140 : 110;
      const dx = link.t.x - link.s.x;
      const dy = link.t.y - link.s.y;
      const dz = link.t.z - link.s.z;
      const distance = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
      const pull = ((distance - want) / distance) * 0.03 * alpha;
      const vs = velocity.get(link.s.id) as Vec3;
      const vt = velocity.get(link.t.id) as Vec3;
      vs.x += dx * pull;
      vs.y += dy * pull;
      vs.z += dz * pull;
      vt.x -= dx * pull;
      vt.y -= dy * pull;
      vt.z -= dz * pull;
    }
    for (const ball of balls) {
      const v = velocity.get(ball.id) as Vec3;
      v.x -= ball.x * 0.012 * alpha;
      v.y -= ball.y * 0.012 * alpha;
      v.z -= ball.z * 0.012 * alpha;
      v.x *= 0.9;
      v.y *= 0.9;
      v.z *= 0.9;
      ball.x += v.x * 0.28;
      ball.y += v.y * 0.28;
      ball.z += v.z * 0.28;
    }
    alpha *= 0.994;
  }
  // 整えた位置を、注目が外れたときに戻る位置として覚える
  for (const ball of balls) ball.home = { x: ball.x, y: ball.y, z: ball.z };
};

/** 画面の外へ出る前に描き続ける余白を足した、画面の中か */
const onScreen = (x: number, y: number, width: number, height: number, margin: number): boolean => {
  return x > -margin && y > -margin && x < width + margin && y < height + margin;
};

/** 名前の横の印を出す、名前の文字の大きさの下限（px。これより小さい名前の玉には出さない） */
const COMMENT_MARK_MIN_FONT = 8;

/** 名前の右端と印の間の隙間（px） */
const COMMENT_MARK_GAP = 4;

/** 玉の名前の横に置いた印（重ねる層に 1 つずつ持つ） */
type MarkSlot = { element: HTMLElement; count: number; width: number; height: number; visible: boolean };

/** 鍵の一辺（px） */
const KEY_SIZE = 12;

/** 名前と鍵の間の隙間（px） */
const KEY_GAP = 3;

/** 状態の印の大きさ（名前の文字の高さに対する割合） */
const STATUS_MARK_SCALE = 0.8;

/** 状態の印と名前の間（名前の文字の高さに対する割合） */
const STATUS_MARK_GAP = 0.4;

/** 鍵の線画（24 の枠）: 閉じた鍵と開いた鍵の輪の部分 */
const LOCK_PATH_DATA = "M7 11V7a5 5 0 0 1 10 0v4";
const UNLOCK_PATH_DATA = "M7 11V7a5 5 0 0 1 9.9-1";

/** 鍵のマーク（24 の枠の線画）を、中心と一辺を指定してキャンバスに描く。振れは鍵の上端を軸にする */
const drawKeyIcon = ({
  context,
  x,
  y,
  size,
  closed,
  color,
  alpha,
  swing,
}: {
  context: CanvasRenderingContext2D;
  x: number;
  y: number;
  size: number;
  closed: boolean;
  color: string;
  alpha: number;
  swing: number;
}): void => {
  context.save();
  context.setLineDash([]);
  context.globalAlpha = alpha;
  context.strokeStyle = color;
  context.lineWidth = 2;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.translate(x, y - size / 2);
  context.rotate(swing);
  context.translate(-size / 2, 0);
  context.scale(size / 24, size / 24);
  context.beginPath();
  context.roundRect(3, 11, 18, 11, 2);
  context.stroke();
  context.stroke(new Path2D(closed ? LOCK_PATH_DATA : UNLOCK_PATH_DATA));
  context.restore();
};

/** 状態の印（一覧と同じ SVG）と資料の成果物の箱を、今の配色で絵にして取っておく（テーマごと） */
const statusImages = new Map<string, HTMLImageElement>();

/** 項目の状態の印の絵を返す。読み込み中は null */
const statusImage = ({ item, ringColor, theme }: { item: Item; ringColor: string; theme: string }): HTMLImageElement | null => {
  const deliverable = item.deliverable === true;
  const cacheKey = `${deliverable ? "deliverable" : (item.status ?? "")}|${theme}`;
  if (!statusImages.has(cacheKey)) {
    const source = deliverable ? staticElement(createElement(Icon, { name: "box" })) : item.status === undefined ? null : staticElement(createElement("span", null, createElement(StatusMark, { status: item.status }))).firstElementChild;
    if (source === null || source === undefined) return null;
    source.removeAttribute("class");
    source.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    source.setAttribute("width", "24");
    source.setAttribute("height", "24");
    if (deliverable) {
      source.setAttribute("fill", "none");
      source.setAttribute("stroke", ringColor);
      source.setAttribute("stroke-width", "2.2");
      source.setAttribute("stroke-linecap", "round");
      source.setAttribute("stroke-linejoin", "round");
    } else {
      source.setAttribute("viewBox", "-1 -1 12 12");
    }
    // CSS の色の変数は絵の中では効かないので、今の値に置き換える
    const style = getComputedStyle(document.documentElement);
    const text = source.outerHTML.replace(/var\((--[\w-]+)\)/g, (_, name: string) => style.getPropertyValue(name).trim());
    const image = new Image();
    image.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(text)}`;
    statusImages.set(cacheKey, image);
  }
  const image = statusImages.get(cacheKey);
  return image !== undefined && image.complete && image.naturalWidth > 0 ? image : null;
};

/** キャンバスと重ねる層を受け取り、視点を全体が収まる向きと距離にして毎コマの描画を始める */
export const createGraphRenderer = ({ canvas, overlay, onPress }: { canvas: HTMLCanvasElement; overlay: HTMLElement; onPress: (id: string | null) => void }): GraphRenderer => {
  const labelCache = new Map<string, HTMLCanvasElement>();
  let colors = readColors();
  let dark = document.documentElement.dataset["theme"] === "dark";
  let lookNow: NetworkLook = "deep";
  let index: RecordIndex | null = null;
  let pending: { graph: Graph; index: RecordIndex } | null = null;
  let destroyed = false;
  let handle = 0;
  /** 名前の横のコメントの印に使う件数 */
  let commentCounts: Record<string, number> = {};
  /** 玉の ID → 名前の横に置いた印 */
  const markSlots = new Map<string, MarkSlot>();
  let balls: Ball[] = [];
  let ballById = new Map<string, Ball>();
  let links: { s: Ball; t: Ball; type: LinkType }[] = [];
  /** 群れのおおよその半径（近い順に 9 割目の玉まで） */
  let reach = 40;
  // 回転は「目標」と「今」を分け、今を目標へ毎コマ少しずつ寄せる（動き出しも止まり際もなめらかにする）
  const camera = {
    yaw: 0.6,
    pitch: -0.25,
    yawTarget: 0.6,
    pitchTarget: -0.25,
    yawSpeed: 0,
    pitchSpeed: 0,
    distance: 520,
    distanceTarget: 520,
    fit: 520,
    center: { x: 0, y: 0, z: 0 },
    centerTarget: { x: 0, y: 0, z: 0 },
  };
  /** ロックの判定をする幅か（幅 900px 以下では詳細が全面に出るので、ロックしない） */
  const wide = media(LOCK_QUERY);
  const reducedMotion = media("(prefers-reduced-motion: reduce)");
  /** 効いているロック（絞り込みで描いていなければ null）。画面を作ったときの値から `setGraphLock` で差し替える */
  let locked: string | null = null;
  let focus: string | null = null;
  let hover: string | null = null;
  /** 詳細パネルで開いている項目 */
  let current: string | null = null;
  let lastInput = 0;
  let birth = performance.now();
  let projected = new Map<string, { sx: number; sy: number; f: number; z: number }>();
  let width = 0;
  let height = 0;
  let dpr = 1;
  /** 鍵が震え始めた時刻 */
  let shakeStart = Number.NEGATIVE_INFINITY;
  /** 直前に押した位置と項目（素早い 2 回目を、詳細が開いて枠がずれても同じ玉への 2 回押しとして扱う） */
  let lastPress: Press | null = null;

  /** 注目の起点: ロックした項目（ロックを判定する幅で、描いている玉のとき）。ロックしていなければ、渡した項目 */
  const anchorOf = (id: string | null): string | null => (wide.matches && locked !== null && ballById.has(locked) ? locked : id);

  /** 玉・太さ・色ごとに、文字を 1 回だけ画像に描いて取っておく */
  const labelImage = (ball: Ball, bold: boolean, color: string): HTMLCanvasElement => {
    const key = `${ball.id}|${bold}|${color}`;
    const cached = labelCache.get(key);
    if (cached !== undefined) return cached;
    const font = (bold ? FONT_BOLD : FONT_NORMAL).replace("10px", `${10 * LABEL_RESOLUTION}px`);
    const image = document.createElement("canvas");
    const measure = image.getContext("2d") as CanvasRenderingContext2D;
    measure.font = font;
    measure.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
    image.width = Math.ceil(measure.measureText(ball.label).width) + 4;
    image.height = LABEL_HEIGHT * LABEL_RESOLUTION;
    const context = image.getContext("2d") as CanvasRenderingContext2D;
    context.font = font;
    context.letterSpacing = `${0.8 * LABEL_RESOLUTION}px`;
    context.fillStyle = color;
    context.textAlign = "center";
    context.textBaseline = "bottom";
    context.fillText(ball.label, image.width / 2, image.height);
    labelCache.set(key, image);
    return image;
  };

  /** 玉の名前の横の印を返す。件数が変わっていれば作り直す（大きさは作ったときに 1 回だけ測る） */
  const markSlotOf = (id: string, count: number): MarkSlot => {
    const slot = markSlots.get(id);
    if (slot !== undefined && slot.count === count) return slot;
    slot?.element.remove();
    const element = staticElement(createElement(CommentMark, { count }));
    element.classList.add("absolute", "left-0", "top-0", "pointer-events-none");
    element.style.visibility = "hidden";
    overlay.append(element);
    const made = { element, count, width: element.offsetWidth, height: element.offsetHeight, visible: false };
    markSlots.set(id, made);
    return made;
  };

  /** 印を見せる・隠す（変わったときだけ触る） */
  const showMark = ({ slot, visible }: { slot: MarkSlot; visible: boolean }): void => {
    if (slot.visible === visible) return;
    slot.visible = visible;
    slot.element.style.visibility = visible ? "" : "hidden";
  };

  /** 玉と線を作る（絞り込みの条件に合う項目で） */
  const rebuild = ({ graph, index: nextIndex }: { graph: Graph; index: RecordIndex }): void => {
    index = nextIndex;
    labelCache.clear();
    balls = placeBalls(nextIndex, graph);
    ballById = new Map(balls.map((ball) => [ball.id, ball]));
    links = graph.links.flatMap((link) => {
      const s = ballById.get(link.source);
      const t = ballById.get(link.target);
      return s === undefined || t === undefined ? [] : [{ s, t, type: link.type }];
    });
    settle(balls, links);
    // 全体が枠に収まる距離（外れた玉に引っぱられないよう、近い順に 9 割目の玉までの半径を使う）
    const radii = balls.map((ball) => Math.hypot(ball.x, ball.y, ball.z)).sort((a, b) => a - b);
    reach = Math.max(40, radii[Math.floor(radii.length * 0.9)] ?? 40);
    const box = Math.max(1, Math.min(canvas.clientWidth || 600, canvas.clientHeight || 460));
    camera.fit = ((FOCAL * reach) / (box * 0.42) + reach * 0.4) * 0.72;
    camera.distance = camera.distanceTarget = camera.fit;
    camera.center = { x: 0, y: 0, z: 0 };
    camera.centerTarget = { x: 0, y: 0, z: 0 };
    birth = performance.now();
    select(current);
  };

  /** 項目を選ぶ（その玉へゆっくり寄る）。ロック中は、ほかの項目を開いても中心と強調をロックした項目に留める。選ぶのをやめたら、全体を見る位置へ戻す */
  const select = (id: string | null): void => {
    current = id;
    const anchor = anchorOf(id);
    const ball = anchor === null ? undefined : ballById.get(anchor);
    focus = ball?.id ?? hover;
    camera.distanceTarget = ball === undefined ? camera.fit : camera.fit * 0.38;
    if (ball === undefined) camera.centerTarget = { x: 0, y: 0, z: 0 };
  };

  /** 見た目を差し替える（玉・線・視点・選んだ項目・ロックは作り直さない） */
  const setLook = (next: NetworkLook): void => {
    lookNow = next;
    // 名前の色は見た目ごとに変わる
    labelCache.clear();
  };

  // ===== 投影 =====
  /** 玉の位置を画面に透視で投影する */
  const project = (point: Vec3) => {
    const cx = point.x - camera.center.x;
    const cy = point.y - camera.center.y;
    const cz = point.z - camera.center.z;
    const cosYaw = Math.cos(camera.yaw);
    const sinYaw = Math.sin(camera.yaw);
    const cosPitch = Math.cos(camera.pitch);
    const sinPitch = Math.sin(camera.pitch);
    const x1 = cx * cosYaw - cz * sinYaw;
    const z1 = cx * sinYaw + cz * cosYaw;
    const y1 = cy * cosPitch - z1 * sinPitch;
    const z2 = cy * sinPitch + z1 * cosPitch;
    const f = FOCAL / (z2 + camera.distance);
    return { sx: width / 2 + x1 * f, sy: height / 2 + y1 * f, f, z: z2 };
  };

  /** 視点の回転だけをかける（中心を引かない。無限に遠い星の向きに使う） */
  const rotate = (point: Vec3): Vec3 => {
    const cosYaw = Math.cos(camera.yaw);
    const sinYaw = Math.sin(camera.yaw);
    const cosPitch = Math.cos(camera.pitch);
    const sinPitch = Math.sin(camera.pitch);
    const x1 = point.x * cosYaw - point.z * sinYaw;
    const z1 = point.x * sinYaw + point.z * cosYaw;
    return { x: x1, y: point.y * cosPitch - z1 * sinPitch, z: point.y * sinPitch + z1 * cosPitch };
  };

  /** 画面のずれを、今の向きで世界の座標のずれに戻す */
  const screenToWorld = (dx: number, dy: number): Vec3 => {
    const cosYaw = Math.cos(camera.yaw);
    const sinYaw = Math.sin(camera.yaw);
    const cosPitch = Math.cos(camera.pitch);
    const sinPitch = Math.sin(camera.pitch);
    const y = dy * cosPitch;
    const z1 = -dy * sinPitch;
    return { x: dx * cosYaw + z1 * sinYaw, y, z: -dx * sinYaw + z1 * cosYaw };
  };

  /** 全体が収まる距離で見たときの倍率（玉と文字の大きさの基準） */
  const baseScale = (): number => FOCAL / camera.fit;
  const radiusOf = (ball: Ball, scale: number): number => ball.radius * 1.05 * (scale / baseScale());

  /** 画面の点にある、いちばん手前の玉 */
  const hitTest = (x: number, y: number): Ball | null => {
    let best: Ball | null = null;
    let bestDepth = Number.POSITIVE_INFINITY;
    for (const ball of balls) {
      const p = projected.get(ball.id);
      if (p === undefined || p.z + camera.distance <= 10) continue;
      const reachOf = Math.max(8, radiusOf(ball, p.f)) + 4;
      if (Math.hypot(p.sx - x, p.sy - y) < reachOf && p.z < bestDepth) {
        best = ball;
        bestDepth = p.z;
      }
    }
    return best;
  };

  // ===== 操作 =====
  /** キャンバスに登録したリスナーを `destroy` でまとめて解除する */
  const listeners = new AbortController();
  const { signal } = listeners;
  let drag: { x: number; y: number; time: number } | null = null;
  let moved = 0;
  canvas.addEventListener("pointerdown", (event) => {
    drag = { x: event.clientX, y: event.clientY, time: performance.now() };
    moved = 0;
    canvas.setPointerCapture?.(event.pointerId);
    lastInput = performance.now();
    camera.yawSpeed = camera.pitchSpeed = 0;
  }, { signal });
  canvas.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();
    if (drag !== null) {
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      const now = performance.now();
      const dt = Math.max(8, now - drag.time);
      moved += Math.abs(dx) + Math.abs(dy);
      camera.yawTarget += dx * 0.0032;
      camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + dy * 0.0032));
      camera.yawSpeed = dx * 0.0032 * (16 / dt);
      camera.pitchSpeed = dy * 0.0032 * (16 / dt);
      drag = { x: event.clientX, y: event.clientY, time: now };
      lastInput = now;
      return;
    }
    const target = hitTest(event.clientX - rect.left, event.clientY - rect.top);
    const id = target?.id ?? null;
    if (id !== hover) {
      hover = id;
      if (anchorOf(current) === null) focus = id;
    }
    canvas.style.cursor = id === null ? "grab" : "pointer";
  }, { signal });
  canvas.addEventListener("pointerleave", () => {
    if (drag === null && hover !== null) {
      hover = null;
      if (anchorOf(current) === null) focus = null;
    }
  }, { signal });
  canvas.addEventListener("pointerup", (event) => {
    const rect = canvas.getBoundingClientRect();
    // ほとんど動かさずに離した: 玉か余白を押した
    if (drag !== null && moved < 5) {
      const hit = hitTest(event.clientX - rect.left, event.clientY - rect.top);
      if (!wide.matches) {
        // 幅 900px 以下ではロックせず、押した玉の項目をそのまま渡す
        onPress(hit?.id ?? null);
      } else {
        // 押した玉（余白なら null）を渡す。素早い 2 回目は前に押した玉への 2 回押しにする
        const press: Press = { time: performance.now(), x: event.clientX, y: event.clientY, id: hit?.id ?? null };
        const pressed = resolvePress({ last: lastPress, press });
        lastPress = press;
        onPress(pressed);
      }
    }
    // 止めてから離したときは滑らせない
    if (drag !== null && performance.now() - drag.time > 80) camera.yawSpeed = camera.pitchSpeed = 0;
    drag = null;
  }, { signal });
  // ホイール: マウスのある位置へ向かって寄る・離れる（距離も中心も目標へなめらかに寄せる）
  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const mx = event.clientX - rect.left - width / 2;
      const my = event.clientY - rect.top - height / 2;
      const old = camera.distanceTarget;
      const next = Math.max(camera.fit * 0.15, Math.min(camera.fit * 2.5, old * Math.exp(event.deltaY * 0.0016)));
      if (anchorOf(current) === null) {
        const f = FOCAL / old;
        const shift = screenToWorld((mx / f) * (1 - next / old), (my / f) * (1 - next / old));
        camera.centerTarget = {
          x: camera.centerTarget.x + shift.x,
          y: camera.centerTarget.y + shift.y,
          z: camera.centerTarget.z + shift.z,
        };
      }
      camera.distanceTarget = next;
      lastInput = performance.now();
      // 中心は群れの中に収め、全体まで離れたら戻す
      const limit = camera.fit * 0.35;
      const length = Math.hypot(camera.centerTarget.x, camera.centerTarget.y, camera.centerTarget.z);
      if (length > limit) {
        camera.centerTarget = {
          x: (camera.centerTarget.x * limit) / length,
          y: (camera.centerTarget.y * limit) / length,
          z: (camera.centerTarget.z * limit) / length,
        };
      }
      if (next >= camera.fit * 0.95 && anchorOf(current) === null) camera.centerTarget = { x: 0, y: 0, z: 0 };
    },
    { passive: false, signal },
  );
  // 背景のダブルクリックで、全体を見る位置へ戻す
  canvas.addEventListener("dblclick", () => {
    if (anchorOf(current) !== null) return;
    camera.centerTarget = { x: 0, y: 0, z: 0 };
    camera.distanceTarget = camera.fit;
  }, { signal });

  // ===== 毎コマの描き =====
  const resize = (): void => {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    width = canvas.clientWidth;
    height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
  };
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  const context = canvas.getContext("2d");

  /** 注目している玉につながる玉を、注目している玉の近くへゆっくり寄せる。注目が外れると元の位置へ戻す */
  const pullNear = (): void => {
    const focused = focus === null ? undefined : ballById.get(focus);
    const near = new Set<string>();
    if (focused !== undefined) {
      for (const link of links) {
        if (link.s.id === focused.id) near.add(link.t.id);
        if (link.t.id === focused.id) near.add(link.s.id);
      }
    }
    for (const ball of balls) {
      const home = ball.home;
      const pivot = focused?.home;
      const goal =
        pivot !== undefined && near.has(ball.id)
          ? {
              x: pivot.x + (home.x - pivot.x) * PULL_KEEP,
              y: pivot.y + (home.y - pivot.y) * PULL_KEEP,
              z: pivot.z + (home.z - pivot.z) * PULL_KEEP,
            }
          : home;
      ball.x += (goal.x - ball.x) * PULL_EASE;
      ball.y += (goal.y - ball.y) * PULL_EASE;
      ball.z += (goal.z - ball.z) * PULL_EASE;
    }
  };

  /** 1 コマ分の線（画面に入るものだけ）を、奥行きの濃さと沈み具合つきで `LookLink` にする */
  const buildLinkViews = ({ ease }: { ease: number }): LookLink[] => {
    const views: LookLink[] = [];
    for (const link of links) {
      const a = projected.get(link.s.id);
      const b = projected.get(link.t.id);
      if (a === undefined || b === undefined) continue;
      if (a.z + camera.distance <= 10 || b.z + camera.distance <= 10) continue;
      if ((a.sx < 0 && b.sx < 0) || (a.sx > width && b.sx > width) || (a.sy < 0 && b.sy < 0) || (a.sy > height && b.sy > height)) continue;
      const depth = Math.max(0, Math.min(1, 1.25 - ((a.z + b.z) / 2 + camera.distance) / (camera.distance * 2.2)));
      views.push({
        from: { x: a.sx, y: a.sy, radius: radiusOf(link.s, a.f) * ease },
        to: { x: b.sx, y: b.sy, radius: radiusOf(link.t, b.f) * ease },
        type: link.type,
        fromColor: colors.kind[link.s.kind],
        toColor: colors.kind[link.t.kind],
        alpha: depth * Math.min(link.s.fade, link.t.fade),
      });
    }
    return views;
  };

  /** 注目している項目とつながる線（この上を光が流れる） */
  const buildFocusLinks = ({ focused, ease }: { focused: string | null; ease: number }): LookLink[] => {
    const views: LookLink[] = [];
    const focusedBall = focused === null ? undefined : ballById.get(focused);
    const from = focused === null ? undefined : projected.get(focused);
    if (focusedBall === undefined || from === undefined) return views;
    for (const link of links) {
      if (link.s.id !== focusedBall.id && link.t.id !== focusedBall.id) continue;
      const other = link.s.id === focusedBall.id ? link.t : link.s;
      const to = projected.get(other.id);
      if (to === undefined) continue;
      if (from.z + camera.distance <= 10 || to.z + camera.distance <= 10) continue;
      views.push({
        from: { x: from.sx, y: from.sy, radius: radiusOf(focusedBall, from.f) * ease },
        to: { x: to.sx, y: to.sy, radius: radiusOf(other, to.f) * ease },
        type: link.type,
        fromColor: colors.kind[focusedBall.kind],
        toColor: colors.kind[other.kind],
        alpha: 1,
      });
    }
    return views;
  };

  // eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ描き方を 1 か所で読めるように保つ
  const frame = (now: number): void => {
    if (destroyed) return;
    handle = requestAnimationFrame(frame);
    if (width === 0) resize();
    if (context === null || document.hidden || width === 0) return;
    // 枠の大きさが決まってから玉を置く
    if (pending !== null) {
      rebuild(pending);
      pending = null;
    }
    if (index === null) return;
    const reduced = reducedMotion.matches;
    pullNear();
    // 離した後の滑りと、何もしていないときのごくゆっくりした自動の回転（動きを減らす設定では回さない）
    if (drag === null) {
      camera.yawTarget += camera.yawSpeed;
      camera.pitchTarget = Math.max(-1.3, Math.min(1.3, camera.pitchTarget + camera.pitchSpeed));
      camera.yawSpeed *= 0.955;
      camera.pitchSpeed *= 0.93;
      if (!reduced && now - lastInput > IDLE_BEFORE_ROTATE_MS && hover === null) camera.yawTarget += AUTO_ROTATE_STEP;
    }
    camera.yaw += (camera.yawTarget - camera.yaw) * 0.07;
    camera.pitch += (camera.pitchTarget - camera.pitch) * 0.07;
    const anchorNow = anchorOf(current);
    const selectedBall = anchorNow === null ? undefined : ballById.get(anchorNow);
    if (selectedBall !== undefined) {
      camera.centerTarget = { x: selectedBall.x, y: selectedBall.y, z: selectedBall.z };
    }
    camera.center.x += (camera.centerTarget.x - camera.center.x) * 0.025;
    camera.center.y += (camera.centerTarget.y - camera.center.y) * 0.025;
    camera.center.z += (camera.centerTarget.z - camera.center.z) * 0.025;
    camera.distance += (camera.distanceTarget - camera.distance) * 0.04;
    // 開いたときは中心から広がる
    const born = Math.min(1, (now - birth) / 1400);
    const ease = 1 - (1 - born) ** 3;

    const focused = focus !== null && ballById.has(focus) ? focus : null;
    const near = new Set<string>(focused === null ? [] : [focused]);
    if (focused !== null) {
      for (const link of links) {
        if (link.s.id === focused) near.add(link.t.id);
        if (link.t.id === focused) near.add(link.s.id);
      }
    }
    const baseK = baseScale();

    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);
    projected = new Map(
      balls.map((ball) => [
        ball.id,
        project({
          x: ball.x * ease + camera.center.x * (1 - ease),
          y: ball.y * ease + camera.center.y * (1 - ease),
          z: ball.z * ease + camera.center.z * (1 - ease),
        }),
      ]),
    );
    // 玉: 奥から順に、大きさ・濃さ・沈み具合を計算して見た目の描き方へ渡す。遠いほど小さく薄く、注目しているときはつながらないものを沈める（詳細を開いている項目は沈めない）
    const order = [...balls].sort((a, b) => (projected.get(b.id)?.z ?? 0) - (projected.get(a.id)?.z ?? 0));
    const views: { ball: Ball; star: LookStar; depth: number; close: number; rank: number }[] = [];
    for (const [rank, ball] of order.entries()) {
      const p = projected.get(ball.id);
      if (p === undefined || p.z + camera.distance <= 10) continue;
      const r0 = radiusOf(ball, p.f);
      // 画面の外の玉は描かない（光のにじみの分だけ余白を広く取る）
      if (!onScreen(p.sx, p.sy, width, height, r0 * 6 + 40) || r0 > Math.max(width, height)) continue;
      const depth = Math.max(0.15, Math.min(1, 1.25 - (p.z + camera.distance) / (camera.distance * 2.2)));
      ball.fade += ((focused !== null && !near.has(ball.id) && ball.id !== current ? 0.18 : 1) - ball.fade) * 0.03;
      // 手前に来すぎた玉は薄くして、奥を隠さないようにする
      const close = Math.min(1, Math.max(0, ((p.z + camera.distance) / camera.distance - 0.08) / 0.2));
      if (close <= 0.02) continue;
      views.push({
        ball,
        depth,
        close,
        rank,
        star: {
          id: ball.id,
          kind: ball.kind,
          degree: ball.degree,
          x: p.sx,
          y: p.sy,
          radius: Math.max(1.2, r0 * ease),
          alpha: (0.35 + 0.55 * depth) * ball.fade * close,
          color: colors.kind[ball.kind],
          selected: ball.id === current,
          hover: ball.id === hover,
          strong: near.has(ball.id) || ball.id === hover,
          seed: ball.seed,
        },
      });
    }
    const lookFrame: LookFrame = {
      context,
      width,
      height,
      dark,
      colors: { line: colors.line, ring: colors.ring, dot: colors.dot },
      now,
      stars: views.map((view) => view.star),
      links: buildLinkViews({ ease }),
      focusLinks: buildFocusLinks({ focused, ease }),
      focusId: focused,
      near,
      rotate,
      project: (point) => {
        const q = project(point);
        return { x: q.sx, y: q.sy, depth: q.z + camera.distance, scale: q.f };
      },
      spread: reach,
      reducedMotion: reduced,
    };
    drawLook({ look: lookNow, frame: lookFrame });
    context.globalCompositeOperation = "source-over";
    context.setLineDash([]);
    // 鍵を置く玉: ロックした項目。ロックしていなければ、詳細を開いている項目
    const lockedNow = anchorOf(null);
    const keyView = wide.matches ? (views.find((view) => view.ball.id === (lockedNow ?? current)) ?? null) : null;
    const keyClosed = keyView !== null && keyView.ball.id === lockedNow;
    // 鍵を出すか: 閉じた鍵はロック中いつも、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ
    const keyShown = keyView !== null && (keyClosed || hover === keyView.ball.id);
    /** 鍵の中心（名前が出ない距離では、玉の右上の札） */
    let keySpot: { x: number; y: number; badge: boolean; alpha: number } | null = null;
    /** このコマに印を置いた玉 */
    const markedBalls = new Set<string>();
    for (const view of views) {
      const { ball, depth, close, rank, star } = view;
      const { x, y, radius } = star;
      const marked = star.selected || star.hover;
      // 名前: 玉と同じ倍率で大きさが変わる（玉の幅に英字 6 文字ほど）。いつもは薄く、注目している項目とつながる項目ははっきり出す
      const scale = (projected.get(ball.id)?.f ?? baseK) / baseK;
      const fontSize = 4.6 * scale;
      const alpha = (star.strong ? 0.85 : 0.42 * ball.fade) * depth ** 1.4 * Math.max(0, Math.min(1, (fontSize - 3.5) / 2.5));
      if (!(alpha > 0.03 && ease > 0.9 && onScreen(x, y - radius, width, height, 400))) continue;
      const color = star.selected ? colors.ring : lookLabelColor({ look: lookNow, dark, fallback: colors.label });
      // 毎コマ文字を作らず、画像に倍率をかけて置く
      const image = labelImage(ball, marked, color);
      const k = (dpr * fontSize) / 10 / LABEL_RESOLUTION;
      const nameBottom = y - radius * (LABEL_LIFT[lookNow] ?? 1) - 3 * scale;
      context.globalAlpha = alpha * close;
      context.setTransform(k, 0, 0, k, dpr * x, dpr * nameBottom);
      context.drawImage(image, -image.width / 2, -image.height);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      const nameWidth = (image.width / LABEL_RESOLUTION) * (fontSize / 10);
      const nameHeight = LABEL_HEIGHT * (fontSize / 10);
      const nameCenterY = nameBottom - nameHeight / 2;
      const nameRight = x + nameWidth / 2;
      // 状態の印: 注目しているときだけ、起点とつながる項目の名前の左に、名前と同じ濃さで置く（資料の成果物は箱）
      const item = index.byId.get(ball.id)?.item;
      if (selectedBall !== undefined && near.has(ball.id) && item !== undefined) {
        const statusMarkImage = statusImage({ item, ringColor: colors.ring, theme: dark ? "dark" : "light" });
        if (statusMarkImage !== null) {
          const size = fontSize * STATUS_MARK_SCALE;
          context.globalAlpha = alpha * close;
          context.drawImage(statusMarkImage, x - nameWidth / 2 - fontSize * STATUS_MARK_GAP - size, nameCenterY - size / 2, size, size);
        }
      }
      // コメントの印: 名前を文字 8px 以上で描いた、件数のある玉に、名前と同じ濃さで置く。名前・鍵・コメントの印の順で、鍵を出すときだけ鍵の幅を空ける
      const count = commentCounts[ball.id] ?? 0;
      const slot = count > 0 && fontSize >= COMMENT_MARK_MIN_FONT ? markSlotOf(ball.id, count) : null;
      const keyHere = view === keyView && keyShown;
      const left = nameRight + (keyHere ? KEY_GAP + KEY_SIZE : 0) + COMMENT_MARK_GAP;
      if (keyHere) keySpot = { x: nameRight + KEY_GAP + KEY_SIZE / 2, y: nameCenterY, badge: false, alpha: alpha * close };
      if (slot !== null) {
        const top = nameCenterY - slot.height / 2;
        // 名前と印が描く枠（上端は名前か印の高いほう、下端は低いほう）が、キャンバスに収まるときだけ置く
        const frameTop = Math.min(top, nameCenterY - nameHeight / 2);
        const frameBottom = Math.max(top + slot.height, nameCenterY + nameHeight / 2);
        const fits = x - nameWidth / 2 >= 0 && left + slot.width <= width && frameTop >= 0 && frameBottom <= height;
        if (fits) {
          slot.element.style.transform = `translate(${left}px, ${top}px)`;
          slot.element.style.opacity = String(alpha * close);
          // 手前の玉ほど上に重ねる（重なり順は層の中に閉じる）
          slot.element.style.zIndex = String(rank + 1);
          showMark({ slot, visible: true });
          markedBalls.add(ball.id);
        }
      }
    }
    // 鍵: 閉じた鍵はロック中いつも、開いた鍵は詳細を開いている玉にカーソルを乗せたときだけ出す。押しても何も起きない
    if (keyView !== null && keyShown) {
      // 名前が出ていない遠い距離では、玉の右上に札に入れて置く
      const spot = keySpot ?? { x: keyView.star.x + keyView.star.radius * 0.8 + 8, y: keyView.star.y - keyView.star.radius * 0.8 - 8, badge: true, alpha: 1 };
      // 外れない操作をされた直後は、赤くして左右に震わせ、だんだん収める（CSS のアニメーションに頼らず毎コマ当てるので、動きを減らす設定でも止めない）
      const elapsed = now - shakeStart;
      const shaking = keyClosed && elapsed < SHAKE_MS;
      const { decay, wave } = shaking ? shakeAt(elapsed) : { decay: 0, wave: 0 };
      const keyX = spot.x + wave * SHAKE_SHIFT * decay;
      const red = shakeColor();
      const keyColor = shaking ? red : keyClosed ? colors.ring : colors.label;
      if (shaking) {
        context.globalAlpha = 0.55 * decay;
        context.drawImage(bakeGlow({ color: red, falloff: 2 }), keyX - 22, spot.y - 22, 44, 44);
      }
      if (spot.badge) {
        context.globalAlpha = keyClosed ? 0.95 : 0.6;
        context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
        context.beginPath();
        context.arc(keyX, spot.y, KEY_SIZE * 0.85, 0, Math.PI * 2);
        context.fill();
        context.strokeStyle = keyColor;
        context.lineWidth = 1;
        context.stroke();
      }
      drawKeyIcon({
        context,
        x: keyX,
        y: spot.y,
        size: KEY_SIZE * (1 + SHAKE_GROW * decay),
        closed: keyClosed,
        color: keyColor,
        alpha: keyClosed ? 0.95 : 0.45,
        swing: wave * SHAKE_SWING * decay,
      });
    }
    context.globalAlpha = 1;
    // このコマに置かなかった印は隠し、件数が無くなった玉の印は外す
    for (const [id, slot] of markSlots) {
      if (markedBalls.has(id)) continue;
      showMark({ slot, visible: false });
      if ((commentCounts[id] ?? 0) === 0) {
        slot.element.remove();
        markSlots.delete(id);
      }
    }
  };

  // 文字の書体が読み込まれたら、取っておいた文字の画像を作り直す
  const clearLabels = (): void => {
    labelCache.clear();
  };
  document.fonts?.addEventListener("loadingdone", clearLabels);
  handle = requestAnimationFrame(frame);
  return {
    setGraph: (input) => {
      pending = input;
    },
    setLook,
    setTheme: (theme) => {
      dark = theme === "dark";
      colors = readColors();
      labelCache.clear();
    },
    setFocus: ({ selectedId, lockedId }) => {
      locked = lockedId;
      select(selectedId);
    },
    setComments: (counts) => {
      commentCounts = counts;
    },
    shake: () => {
      shakeStart = performance.now();
    },
    destroy: () => {
      destroyed = true;
      cancelAnimationFrame(handle);
      listeners.abort();
      observer.disconnect();
      document.fonts?.removeEventListener("loadingdone", clearLabels);
      for (const slot of markSlots.values()) slot.element.remove();
      markSlots.clear();
    },
  };
};
