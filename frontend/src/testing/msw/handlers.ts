// 配信の API の MSW の handler（Storybook・Vitest で共有する）
import { http, HttpResponse } from "msw";

// 概要とトップバーが読む記録の最小の形
export const RECORDS = {
  settings: {
    summary: "要件出しのスキル mindmap を設計する",
    playbooks: ["システム開発"],
    target_label: "対象",
    phases: ["目的", "要件"],
    targets: [{ name: "スキル", summary: "" }],
    categories: [{ name: "記録", target: "スキル", summary: "" }],
  },
  decisions: [
    { id: "D-1", title: "D-1の題", status: "未決定", category: "記録", phase: "目的" },
    { id: "D-3", title: "D-3の題", status: "要見直し", category: "記録", phase: "要件" },
  ],
  tasks: [{ id: "T-1", title: "T-1の題", status: "進行中" }],
  research: [],
  docs: [],
  terms: [],
  notes: [],
  logs: [],
  bodies: {},
  marked_bodies: {},
  changes: { last_seq: 0, sets: [], pending: { added: [], changed: [] } },
  derived: {
    next: [{ id: "D-1", title: "D-1の題", phase: "目的", weight: "大", followers: 0 }],
    goal: {
      has_goal: false,
      reached: null,
      goal_phase: null,
      phases: ["目的", "要件"],
      remaining_decisions: [],
      remaining_deliverables: [],
      phase_progress: [
        { phase: "目的", settled: 0, total: 1 },
        { phase: "要件", settled: 0, total: 1 },
      ],
    },
    progress: [
      {
        category: "記録",
        cells: [
          { phase: "目的", settled: 0, total: 1 },
          { phase: "要件", settled: 0, total: 1 },
        ],
        settled: 0,
        total: 2,
      },
    ],
  },
  built_at: "2026-11-04T02:21:00+00:00",
  settings_problem: null,
};

export const handlers = [
  http.get("/api/records", () => HttpResponse.json(RECORDS)),
  http.get("/api/comments", () => HttpResponse.json({ items: [{ id: "C-1" }, { id: "C-2" }], drafts: [] })),
  http.get("/api/edits", () => HttpResponse.json({ items: [] })),
  http.get("/api/threads", () => HttpResponse.json({ threads: [] })),
];
