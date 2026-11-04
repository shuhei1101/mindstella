// 配信の API の MSW の handler（Storybook・Vitest で共有する）
import { http, HttpResponse } from "msw";

// 概要とトップバーが読む記録の最小の形
export const RECORDS = {
  settings: { summary: "要件出しのスキル mindmap を設計する", playbooks: ["システム開発"], phases: ["目的", "要件"] },
  decisions: [
    { id: "D-1", title: "D-1の題", status: "未決定", phase: "目的" },
    { id: "D-3", title: "D-3の題", status: "要見直し", phase: "要件" },
  ],
  tasks: [{ id: "T-1", title: "T-1の題", status: "進行中" }],
  research: [],
  docs: [],
  terms: [],
  notes: [],
  logs: [],
  bodies: {},
  marked_bodies: {},
  changes: [],
  derived: {
    next: [{ id: "D-1", impact: 3, followers: 0 }],
    goal: { has_goal: true, decided: 0, total: 2, stages: [], remaining_deliverables: [] },
    progress: { rows: [] },
  },
  built_at: "2026-11-04T02:21:00+00:00",
  settings_problem: null,
};

export const handlers = [
  http.get("/api/records", () => HttpResponse.json(RECORDS)),
  http.get("/api/comments", () => HttpResponse.json({ items: [{ id: "C-1" }, { id: "C-2" }], drafts: {} })),
  http.get("/api/edits", () => HttpResponse.json({ items: [] })),
  http.get("/api/threads", () => HttpResponse.json({ threads: [] })),
];
