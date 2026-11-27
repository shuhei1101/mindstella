// 配信の API の MSW の handler（Storybook・Vitest で共有する）
import { http, HttpResponse } from "msw";

// 概要とトップバーが読む記録の最小の形
export const RECORDS = {
  settings: { summary: "要件出しのスキル mindmap を設計する", links: [] },
  decisions: [
    { id: "D-1", title: "D-1の題", status: "未決定" },
    { id: "D-3", title: "D-3の題", status: "要見直し" },
  ],
  tasks: [{ id: "T-1", title: "T-1の題", status: "進行中" }],
  research: [],
  docs: [{ id: "A-1", title: "A-1の題", status: "確認中" }],
  terms: [],
  notes: [],
  logs: [],
  bodies: {},
  marked_bodies: {},
  changes: { last_seq: 0, sets: [], pending: { added: [], changed: [] } },
  derived: { ready: ["D-1"] },
  built_at: "2026-11-04T02:21:00+00:00",
  settings_problem: null,
};

export const handlers = [
  http.get("*/api/records", () => HttpResponse.json(RECORDS)),
  http.get("*/api/comments", () => HttpResponse.json({ items: [{ id: "C-1" }, { id: "C-2" }], drafts: [] })),
  http.get("*/api/edits", () => HttpResponse.json({ items: [] })),
  http.get("*/api/threads", () => HttpResponse.json({ threads: [] })),
  http.post("*/api/edits", () => HttpResponse.json({ id: "E-1", target: "D-1", count: 1 }, { status: 201 })),
  http.delete("*/api/edits/:id", ({ params }) => HttpResponse.json({ removed: [params["id"]], count: 0 })),
  http.post("*/api/edits/save", () => HttpResponse.json({ set: "V-1", at: "2026-11-04T02:21:00+00:00", added: [], changed: [], removed: [], settings: [] })),
  http.post("*/api/comments", () => HttpResponse.json({ id: "C-3", created: "2026-11-04T02:21:00+00:00", count: 3 }, { status: 201 })),
  http.patch("*/api/comments/:id", async ({ params, request }) => HttpResponse.json({ id: params["id"], body: "", loc: null, ...((await request.json()) as object) })),
  http.delete("*/api/comments/:id", ({ params }) => HttpResponse.json({ id: params["id"], target: null, loc: null, thread: null, body: "", created: "2026-11-04T02:21:00+00:00", count: 1 })),
  http.post("*/api/comments/send", () => HttpResponse.json({ sent: "2026-11-04T02:21:00+00:00", items: [], entered: true }, { status: 201 })),
  http.put("*/api/drafts", () => new HttpResponse(null, { status: 204 })),
  http.patch("*/api/threads/:id", async ({ params, request }) => HttpResponse.json({ id: params["id"], status: ((await request.json()) as { status: string }).status, changed: true })),
  http.post("*/api/threads/:id/seen", ({ params }) => HttpResponse.json({ id: params["id"], seen: [] })),
  http.put("*/api/config/display", async ({ request }) => HttpResponse.json({ display: await request.json() })),
];
