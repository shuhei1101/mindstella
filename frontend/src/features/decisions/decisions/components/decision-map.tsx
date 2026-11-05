// 検討事項のマップ。木を elkjs で配置して描き、拡大・全体を表示・キーワードの強調と、狭い幅の字下げの一覧を持つ
import { useEffect, useRef, useState } from "react";

import { DecisionOutline } from "@/features/decisions/decisions/components/decision-outline";
import { buildMapGraph, dependencyPath, layoutMap, wheelZoom, ZOOM, type Elk, type MapGraph, type MapNode } from "@/features/decisions/decisions/map-layout";
import { useLibrary } from "@/shared/adapters/libraries";
import { CommentMark } from "@/shared/components/comment-mark";
import { DiffMark, type DiffMarks } from "@/shared/components/diff-mark";
import { Icon, StatusMark } from "@/shared/components/icon";
import { PendingMark } from "@/shared/components/pending-mark";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import type { ScreenEdit } from "@/shared/core/edits";
import type { Item, Settings } from "@/shared/core/records";
import { cn } from "@/shared/lib/cn";

const FIT_MARGIN = 16;
const FIT_RIGHT = 240;
const FIT_BOTTOM = 160;
const ZOOM_FROM_FIT = 0.6;

export type DecisionMapProps = {
  items: readonly Item[];
  settings: Settings;
  selectedId: string | undefined;
  marks?: DiffMarks | undefined;
  comments?: Record<string, number>;
  edit?: ScreenEdit | null;
  onOpen: (id: string) => void;
  onClear?: () => void;
};

const NODE_TONE: Record<Exclude<MapNode["kind"], "item">, string> = {
  target: "bg-primary text-primary-foreground font-semibold",
  category: "bg-secondary font-medium",
  phase: "bg-muted text-xs text-muted-foreground",
};

export const DecisionMap = ({ items, settings, selectedId, marks, comments = {}, edit = null, onOpen, onClear }: DecisionMapProps) => {
  const { status, library } = useLibrary("elkjs");
  const wrap = useRef<HTMLDivElement>(null);
  const [laid, setLaid] = useState<MapGraph | null>(null);
  const [zoom, setZoom] = useState<number | "fit">("fit");
  const [fitScale, setFitScale] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [locked, setLocked] = useState<string | null>(null);
  const key = items.map((item) => item.id).join(",");
  useEffect(() => {
    if (status !== "ready") return undefined;
    let alive = true;
    const ElkClass = library as new () => Elk;
    void layoutMap(buildMapGraph(items, settings), new ElkClass()).then((graph) => {
      if (alive) setLaid(graph);
    });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 描く項目の並びが変わったときだけ配置する
  }, [status, library, key]);
  useEffect(() => {
    const element = wrap.current;
    if (element === null || laid === null) return undefined;
    const update = (): void => {
      setFitScale(Math.min(1, (element.clientWidth - FIT_MARGIN) / (laid.width ?? 1), (element.clientHeight - FIT_MARGIN) / (laid.height ?? 1)));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [laid]);
  const scale = zoom === "fit" ? fitScale : zoom;
  const focus = locked ?? selectedId ?? null;
  // 開いた節を中央へ送る
  useEffect(() => {
    const element = wrap.current;
    const node = laid?.nodes.find((candidate) => candidate.id === focus);
    if (element === null || node === undefined) return;
    element.scrollTo({ left: ((node.x ?? 0) + node.width / 2) * scale - element.clientWidth / 2, top: ((node.y ?? 0) + node.height / 2) * scale - element.clientHeight / 2 });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 起点が変わったときだけ送る
  }, [focus, laid]);
  if (status === "failed") {
    return (
      <div>
        <p role="alert" className="text-small text-muted-foreground">
          elkjs を読み込めないため、マップを出せません。
        </p>
        <p className="text-small text-muted-foreground">表示形式を「表」に切り替えると、検討事項を表示できます。</p>
      </div>
    );
  }
  const byId = new Map(laid?.nodes.map((node) => [node.id, node]) ?? []);
  const parentOf = new Map(laid?.edges.map((edge) => [edge.targets[0], edge.sources[0]]) ?? []);
  const chain = new Set<string>();
  for (let id: string | undefined = focus ?? undefined; id !== undefined; id = parentOf.get(id)) chain.add(id);
  const near = new Set(chain);
  const dependencies = (laid?.nodes ?? []).flatMap((node) =>
    (node.item?.depends_on ?? []).flatMap((prerequisite) => {
      const from = byId.get(prerequisite);
      if (from === undefined) return [];
      const related = focus !== null && (focus === prerequisite || focus === node.id);
      if (related) {
        near.add(prerequisite);
        near.add(node.id);
      }
      return [{ id: `dep-${prerequisite}-${node.id}`, path: dependencyPath(from, node), related, incoming: node.id === focus }];
    }),
  );
  const lowered = keyword.toLowerCase();
  const press = (id: string): void => {
    // 詳細を開いている節をもう一度押すとロックし、ロックした節を開いてもう一度押すと外す（今の画面の `lockTap`）
    if (id === selectedId) setLocked(locked === id ? null : (locked ?? id));
    else onOpen(id);
  };
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">
      <Input type="search" placeholder="タイトルで強調" aria-label="タイトルで強調するキーワード" value={keyword} className="max-w-60" onChange={(event) => { setKeyword(event.target.value); }} />
      {items.length === 0 ? <p className="text-small text-muted-foreground">表示する検討事項はありません。</p> : null}
      {/* 余白の押下は選びを外すだけの補助で、詳細を閉じるボタンがキーボードの手段になる */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <div
        ref={wrap}
        className="relative min-h-0 flex-1 overflow-auto rounded-control border border-border-soft max-lg:hidden"
        onWheel={(event) => {
          const element = wrap.current;
          if (element === null || event.deltaY === 0 || laid === null) return;
          const box = element.getBoundingClientRect();
          const next = wheelZoom({ scale, deltaY: event.deltaY, point: { x: event.clientX - box.left, y: event.clientY - box.top }, scroll: { left: element.scrollLeft, top: element.scrollTop } });
          setZoom(next.scale);
          element.scrollTo(next.scroll);
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget && locked === null) onClear?.();
        }}
      >
        {laid === null ? null : (
          <div style={{ width: (laid.width ?? 0) * scale + (zoom === "fit" ? FIT_RIGHT : 0), height: (laid.height ?? 0) * scale + (zoom === "fit" ? FIT_BOTTOM : 0) }}>
            <div id="decision-map" role="group" aria-label="検討事項のマップ" className="relative origin-top-left" style={{ width: laid.width, height: laid.height, transform: `scale(${String(scale)})` }}>
              <svg className="absolute inset-0 text-border" width={laid.width} height={laid.height} aria-hidden="true" fill="none" stroke="currentColor">
                {laid.edges.map((edge) => {
                  const section = edge.sections?.[0];
                  if (section === undefined) return null;
                  const points = [section.startPoint, ...(section.bendPoints ?? []), section.endPoint];
                  const related = chain.has(edge.sources[0] ?? "") && chain.has(edge.targets[0] ?? "");
                  return <path key={edge.id} d={`M${points.map((point) => `${String(point.x)},${String(point.y)}`).join(" L")}`} className={cn(related && "text-mark")} stroke="currentColor" />;
                })}
                {dependencies.map(({ id, path, related, incoming }) => (
                  <g key={id}>
                    <path id={id} d={path} strokeDasharray="4 4" className={cn(related && "text-mark")} stroke="currentColor" />
                    {related
                      ? [0, 1.6].map((begin) => (
                          <circle key={begin} r="2.6" className="fill-mark" stroke="none">
                            <animateMotion dur="3.2s" begin={`${String(begin)}s`} repeatCount="indefinite" {...(incoming ? { keyPoints: "1;0", keyTimes: "0;1", calcMode: "linear" } : {})}>
                              <mpath href={`#${id}`} />
                            </animateMotion>
                          </circle>
                        ))
                      : null}
                  </g>
                ))}
              </svg>
              {/* eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ */}
              {laid.nodes.map((node) => {
                const box = { left: node.x ?? 0, top: node.y ?? 0, width: node.width, height: node.height };
                const dimmed = focus !== null && !near.has(node.id);
                const { item } = node;
                if (node.kind === "item" && item !== undefined) {
                  const mark = marks?.[item.id];
                  const pending = edit?.marks[item.id];
                  const count = comments[item.id] ?? 0;
                  const hit = lowered !== "" && item.title.toLowerCase().includes(lowered);
                  return (
                    <button key={node.id} type="button" data-node={item.id} style={box} title={`${item.title}（${item.status ?? ""}）`} className={cn("absolute flex cursor-pointer flex-col justify-center gap-0.5 rounded-control border border-border bg-card px-2 text-left text-xs", dimmed && "opacity-50", selectedId === item.id && "border-mark bg-row-selected", hit && "bg-hit")} onClick={() => { press(item.id); }}>
                      <span className="flex items-center gap-1 text-small">
                        <StatusMark status={item.status} />
                        <span className="min-w-0 flex-1 truncate">{item.title}</span>
                        {locked === item.id ? <Icon name="lock" className="size-3 flex-none" /> : null}
                      </span>
                      <span className="flex items-center gap-1 text-muted-foreground">
                        {mark === undefined ? null : <DiffMark kind={mark} />}
                        <span className="font-mono">{item.id}</span>
                        <span>{item.status}</span>
                        {item.weight === undefined ? null : <span>影響度 {item.weight}</span>}
                        {pending === undefined ? null : <PendingMark kind={pending} compact />}
                        {count > 0 ? <CommentMark count={count} /> : null}
                      </span>
                    </button>
                  );
                }
                return (
                  <div key={node.id} data-node={node.id} style={box} className={cn("absolute flex items-center rounded-control px-2 text-small", NODE_TONE[node.kind as Exclude<MapNode["kind"], "item">], dimmed && "opacity-50")}>
                    <span className="truncate">{node.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
      <div role="group" aria-label="拡大率" className="flex items-center gap-1 self-end max-lg:hidden">
        <Button variant="ghost" size="icon" aria-label="縮小" onClick={() => { setZoom(Math.max(ZOOM.min, Math.round(((zoom === "fit" ? ZOOM_FROM_FIT : zoom) - ZOOM.step) * 100) / 100)); }}>
          −
        </Button>
        <Button variant="ghost" aria-pressed={zoom === "fit"} onClick={() => { setZoom(zoom === "fit" ? 1 : "fit"); }}>
          全体を表示
        </Button>
        <Button variant="ghost" size="icon" aria-label="拡大" onClick={() => { setZoom(Math.min(ZOOM.max, Math.round(((zoom === "fit" ? ZOOM_FROM_FIT : zoom) + ZOOM.step) * 100) / 100)); }}>
          ＋
        </Button>
      </div>
      <DecisionOutline items={items} settings={settings} marks={marks} comments={comments} edit={edit} onOpen={onOpen} />
    </div>
  );
};
