// 見本の記録の足し分: #237 の見本の記録（data.js が埋め込み先へ入れたもの）のタスクに、予定（plan）と実績（actual）を足す
// 4 つとも持つタスク・予定だけ・実績だけ・片方の日付だけ・どれも持たないタスクを混ぜ、値の無いキーを出さない見本にする
(() => {
  const element = document.getElementById("mindmap-data");
  const data = JSON.parse(element.textContent);

  /** タスクの ID → 予定と実績（書かないキーは持たない） */
  const dates = {
    "T-1": { plan: { start: "2026-10-01", due: "2026-10-03" }, actual: { started: "2026-10-02", done: "2026-10-03" } },
    "T-2": { plan: { start: "2026-10-05", due: "2026-10-10" }, actual: { started: "2026-10-06" } },
    "T-3": { plan: { due: "2026-10-15" } },
    "T-4": { plan: { start: "2026-10-02", due: "2026-10-03" }, actual: { started: "2026-10-03", done: "2026-10-03" } },
    "T-5": { plan: { start: "2026-10-06", due: "2026-10-12" }, actual: { started: "2026-10-07" } },
    "T-8": { actual: { started: "2026-10-06" } },
    "T-9": { plan: { start: "2026-10-12", due: "2026-10-16" } },
    "T-12": { actual: { started: "2026-10-06", done: "2026-10-06" } },
    "T-13": { plan: { start: "2026-10-14" } },
    "T-14": { plan: { start: "2026-10-05", due: "2026-10-08" }, actual: { started: "2026-10-06" } },
  };
  for (const task of data.tasks) Object.assign(task, dates[task.id] ?? {});

  element.textContent = JSON.stringify(data);
})();
