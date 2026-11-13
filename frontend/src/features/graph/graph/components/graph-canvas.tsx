// 3D のキャンバスと重ねる層。毎コマの描画は React の外の `GraphRenderer` に任せ、props の変化を差し替えの関数で同期する
import { useEffect, useRef } from "react";

import type { Graph } from "@/features/graph/graph/graph-model";
import { createGraphRenderer, type GraphRenderer } from "@/features/graph/graph/graph-renderer";
import type { NetworkLook, RecordIndex } from "@/shared/core/records";
import { useThemeStore } from "@/shared/stores/theme-store";

export type GraphCanvasProps = {
  graph: Graph;
  index: RecordIndex;
  look: NetworkLook;
  selectedId: string | null;
  lockedId: string | null;
  comments: Record<string, number>;
  /** 増えるたびに閉じた鍵を震わせる */
  shakeSignal: number;
  onPress: (id: string | null) => void;
};

export const GraphCanvas = ({ graph, index, look, selectedId, lockedId, comments, shakeSignal, onPress }: GraphCanvasProps) => {
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const renderer = useRef<GraphRenderer | null>(null);
  const press = useRef(onPress);
  const theme = useThemeStore((state) => state.theme);
  useEffect(() => {
    press.current = onPress;
  });
  // 描画を始め、外したら止める（React の外のシステムとの同期）
  useEffect(() => {
    if (canvas.current === null || overlay.current === null) return;
    const made = createGraphRenderer({ canvas: canvas.current, overlay: overlay.current, onPress: (id) => { press.current(id); } });
    renderer.current = made;
    return () => {
      made.destroy();
      renderer.current = null;
    };
  }, []);
  useEffect(() => {
    renderer.current?.setGraph({ graph, index });
  }, [graph, index]);
  useEffect(() => {
    renderer.current?.setLook(look);
  }, [look]);
  useEffect(() => {
    renderer.current?.setTheme(theme);
  }, [theme]);
  useEffect(() => {
    renderer.current?.setFocus({ selectedId, lockedId });
  }, [selectedId, lockedId]);
  useEffect(() => {
    renderer.current?.setComments(comments);
  }, [comments]);
  useEffect(() => {
    if (shakeSignal > 0) renderer.current?.shake();
  }, [shakeSignal]);
  return (
    <div className="relative min-h-0 flex-1">
      <canvas ref={canvas} id="graph-canvas" role="img" aria-label="すべての項目のネットワーク。L キーで、詳細を開いている項目をロック・解除" className="absolute inset-0 size-full cursor-grab touch-none" />
      <div ref={overlay} className="pointer-events-none absolute inset-0 isolate overflow-hidden" />
    </div>
  );
};
