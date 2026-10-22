// 設定の画面。ワークスペースの設定を、キーごとの入力で書き換える別の画面。

namespace MindmapPreview {
  /** 使っている件数を数える設定のキー */
  export type UsedSettingKey = "phases" | "targets" | "categories" | "tags";

  /** 設定の画面の引数 */
  export type WorkspaceSettingsProps = {
    /** 保存待ちの編集を当てた設定 */
    settings: Settings;
    /** 編集を当てた記録の索引（使われている値の件数を数える） */
    index: RecordIndex;
    /** 設定のキー → 印の種類 */
    marks: Record<string, PendingMarkKind>;
    /** 設定のキー → 溜められなかった理由 */
    errors: Record<string, string>;
    /** タグの件数に数えるスレッド（無ければ項目だけ） */
    threads?: Thread[];
    on: {
      /** 設定のキーを溜める */
      change: (input: { key: string; value: unknown; map?: Record<string, string | null> }) => void;
      close: () => void;
    };
  };

  /** 1 行ずつの表の列（キー・見出し・入力の種類） */
  type TableColumn = { key: string; title: string; type: "text" | "url" };

  /** 1 行ずつの表で書き換える設定のキーと、列 */
  const TABLES: Record<"targets" | "categories" | "links", { label: string; columns: TableColumn[] }> = {
    targets: {
      label: "対象",
      columns: [
        { key: "name", title: "名前", type: "text" },
        { key: "summary", title: "説明", type: "text" },
      ],
    },
    categories: {
      label: "カテゴリー",
      columns: [
        { key: "name", title: "名前", type: "text" },
        { key: "target", title: "対象", type: "text" },
        { key: "summary", title: "説明", type: "text" },
      ],
    },
    links: {
      label: "関連する場所",
      columns: [
        { key: "title", title: "表示名", type: "text" },
        { key: "url", title: "URL", type: "url" },
      ],
    },
  };

  /** 設定のまとまり（見出しとキー） */
  const GROUPS: { title: string; keys: string[] }[] = [
    { title: "話し合い", keys: ["summary", "description", "playbooks", "goal"] },
    { title: "進め方", keys: ["phases", "target_label", "targets", "categories"] },
    { title: "タグと関連", keys: ["tags", "links"] },
    { title: "変更履歴", keys: ["history_limit"] },
  ];

  /** 設定のキーの入力欄の名前 */
  const SETTING_NAMES: Record<string, string> = {
    summary: "題名",
    description: "説明",
    playbooks: "プレイブック",
    goal: "ゴール",
    phases: "フェーズ",
    target_label: "最上位の軸の呼び名",
    targets: "対象",
    categories: "カテゴリー",
    tags: "タグの語彙",
    links: "関連する場所",
    history_limit: "保持する回数",
  };

  /** タグを外す付け替え先の選択肢 */
  const DROP_TAG = "タグから外す";

  /** フェーズ・対象・カテゴリー・タグの 1 つの値を持つ項目（タグはスレッドも）の件数 */
  export function usageCount({
    index,
    threads,
    key,
    value,
  }: {
    index: RecordIndex;
    threads: readonly Thread[];
    key: UsedSettingKey;
    value: string;
  }): number {
    let count = 0;
    for (const { item } of index.byId.values()) {
      if (key === "phases" && item.phase === value) count += 1;
      if (key === "targets" && item.target === value) count += 1;
      if (key === "categories" && item.category === value) count += 1;
      if (key === "tags" && (item.tags ?? []).includes(value)) count += 1;
    }
    if (key === "targets") count += index.data.settings.categories.filter((category) => category.target === value).length;
    if (key === "tags") count += threads.filter((thread) => thread.tags.includes(value)).length;
    return count;
  }

  /** 設定の画面（見出しの帯と、まとまりごとの入力）を返す */
  export function workspaceSettings(props: WorkspaceSettingsProps): HTMLElement {
    const form = h({
      tag: "form",
      attrs: {
        class: "pe-form pe-ws-form",
        novalidate: true,
        "aria-label": "ワークスペースの設定",
        onsubmit: (event: Event) => event.preventDefault(),
      },
      children: GROUPS.map((group) =>
        h({
          tag: "fieldset",
          attrs: { class: "pe-ws-group" },
          children: [h({ tag: "legend", children: [group.title] }), ...group.keys.map((key) => settingField({ props, key }))],
        }),
      ),
    });
    form.append(h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
    return h({
      tag: "main",
      attrs: { class: "content pe-ws pe-screen" },
      children: [
        h({
          tag: "div",
          attrs: { class: "pe-screen-head" },
          children: [
            h({ tag: "h1", attrs: { tabindex: "-1" }, children: ["設定"] }),
            h({ tag: "span", attrs: { class: "spacer" } }),
            h({
              tag: "button",
              attrs: { class: "btn", type: "button", onclick: () => props.on.close() },
              children: [icon("x"), "閉じる"],
            }),
          ],
        }),
        form,
      ],
    });
  }

  /** 設定のキー 1 つの入力欄（名前の行・入力・誤り） */
  function settingField({ props, key }: { props: WorkspaceSettingsProps; key: string }): HTMLElement {
    const { settings, marks, errors, on } = props;
    const name = SETTING_NAMES[key] ?? key;
    const controlId = `pe-ws-${key}`;
    const mark = marks[key];
    const wrap = h({
      tag: "div",
      attrs: {
        class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}`,
        "data-key": key,
      },
    });
    const record = settings as unknown as Record<string, unknown>;
    const value = record[key];
    wrap.append(
      h({
        tag: "div",
        attrs: { class: "pe-label-row" },
        children: [
          key === "goal" || key in TABLES || key === "playbooks" || key === "phases" || key === "tags"
            ? h({ tag: "span", attrs: { class: "pe-label", id: `${controlId}-label` }, children: [name] })
            : h({ tag: "label", attrs: { for: controlId, id: `${controlId}-label` }, children: [name] }),
          mark === undefined ? null : pendingEditMark({ kind: mark, compact: true }),
        ],
      }),
    );
    /** 設定のキーを溜める */
    const commit = (next: unknown, map?: Record<string, string | null>): void =>
      on.change(map === undefined ? { key, value: next } : { key, value: next, map });

    if (key === "summary" || key === "target_label") {
      const input = h({
        tag: "input",
        attrs: { id: controlId, class: "input", type: "text", value: typeof value === "string" ? value : "", autocomplete: "off" },
      });
      input.addEventListener("change", () => commit(input.value));
      wrap.append(input);
    } else if (key === "description") {
      const area = h({ tag: "textarea", attrs: { id: controlId, class: "input pe-text", rows: 2 } });
      area.value = typeof value === "string" ? value : "";
      // 空にして離れたら、説明を消す
      area.addEventListener("change", () => commit(area.value === "" ? null : area.value));
      wrap.append(area);
    } else if (key === "history_limit") {
      const input = h({
        tag: "input",
        attrs: {
          id: controlId,
          class: "input pe-num",
          type: "number",
          min: 1,
          step: 1,
          inputmode: "numeric",
          value: typeof value === "number" ? value : "",
        },
      });
      input.addEventListener("change", () => {
        const next = Number(input.value);
        if (input.value.trim() === "" || !Number.isInteger(next) || next < 1) return;
        commit(next);
      });
      wrap.append(input, h({ tag: "p", attrs: { class: "pe-hint" }, children: ["変更履歴に残す書き換えのまとまりの数"] }));
    } else if (key === "playbooks" || key === "phases" || key === "tags") {
      // タグの語彙は名前と説明のオブジェクトの並びなので、チップには名前を出す
      const names = key === "tags" ? (settings.tags ?? []).map((tag) => tag.name) : Array.isArray(value) ? (value as string[]) : [];
      wrap.append(chipsSetting({ props, key, wrap, controlId, name, values: names, commit }));
    } else if (key === "goal") {
      wrap.append(...goalInputs({ props, controlId, commit }));
    } else if (key in TABLES) {
      wrap.append(...tableInputs({ props, key: key as keyof typeof TABLES, controlId, commit }));
    }

    const failure = errors[key];
    if (failure !== undefined) {
      wrap.append(h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [icon("alert"), failure] }));
    }
    return wrap;
  }

  /** 使われている値を外したときの付け替え先の選択（選ぶまで溜めない） */
  function moveSelect({
    key,
    removed,
    count,
    next,
    done,
  }: {
    key: UsedSettingKey;
    removed: string;
    count: number;
    /** 外した後に残る値の並び */
    next: unknown;
    done: (target: string | null) => void;
  }): HTMLElement {
    const remaining = (Array.isArray(next) ? next : []).map((entry) =>
      typeof entry === "string" ? entry : String((entry as { name: string }).name),
    );
    const id = `pe-ws-${key}-move-${safeId(removed)}`;
    const select = h({
      tag: "select",
      attrs: { id, class: "input" },
      children: [
        h({ tag: "option", attrs: { value: "", selected: true }, children: ["選んでください"] }),
        ...remaining.map((entry) => h({ tag: "option", attrs: { value: entry }, children: [entry] })),
        key === "tags" ? h({ tag: "option", attrs: { value: DROP_TAG }, children: [DROP_TAG] }) : null,
      ],
    });
    select.addEventListener("change", () => {
      if (select.value === "") return;
      done(select.value === DROP_TAG ? null : select.value);
    });
    return h({
      tag: "div",
      attrs: { class: "pe-sub pe-move", "data-moving": removed },
      children: [
        h({ tag: "label", attrs: { class: "pe-sub-label", for: id }, children: [`${removed} を使っている ${count} 件の付け替え先`] }),
        select,
        h({ tag: "p", attrs: { class: "pe-hint" }, children: [icon("alert"), "付け替え先を選ぶと保存待ちに入ります。"] }),
      ],
    });
  }

  /** プレイブック・フェーズ・タグの語彙（チップ）。使われているフェーズ・タグを外したときは付け替え先を選ばせる */
  function chipsSetting({
    props,
    key,
    wrap,
    controlId,
    name,
    values,
    commit,
  }: {
    props: WorkspaceSettingsProps;
    key: "playbooks" | "phases" | "tags";
    wrap: HTMLElement;
    controlId: string;
    name: string;
    values: string[];
    commit: (next: unknown, map?: Record<string, string | null>) => void;
  }): HTMLElement {
    const box = h({ tag: "div", attrs: { class: "pe-chips-set" } });
    box.append(
      chipsInput({
        controlId,
        name,
        hint: `${name}を入れる`,
        values,
        vocabulary: null,
        monospace: false,
        disabled: false,
        onChange: (names, removed) => {
          // タグの語彙は、残るタグの説明を保ったまま名前のオブジェクトの並びに戻す
          const next = key === "tags" ? names.map((tag) => props.settings.tags?.find((entry) => entry.name === tag) ?? { name: tag }) : names;
          const used =
            removed !== null && key !== "playbooks"
              ? usageCount({ index: props.index, threads: props.threads ?? [], key, value: removed })
              : 0;
          if (removed === null || used === 0) {
            commit(next);
            return;
          }
          // 使われている値を外した: 付け替え先を選んだときに、対応つきで溜める
          wrap.querySelector(`[data-moving="${removed}"]`)?.remove();
          wrap.append(
            moveSelect({
              key: key as UsedSettingKey,
              removed,
              count: used,
              next,
              done: (target) => commit(next, { [removed]: target }),
            }),
          );
        },
      }),
    );
    return box;
  }

  /** ゴール（届けるフェーズ・ゴールの中身を書き換え、納品物は読むだけで並べる） */
  function goalInputs({
    props,
    controlId,
    commit,
  }: {
    props: WorkspaceSettingsProps;
    controlId: string;
    commit: (next: unknown) => void;
  }): HTMLElement[] {
    const { settings } = props;
    const goal = settings.goal ?? { phase: settings.phases[0] ?? "", summary: "", deliverables: [] };
    const phase = h({
      tag: "select",
      attrs: { id: `${controlId}-phase`, class: "input" },
      children: settings.phases.map((entry) =>
        h({ tag: "option", attrs: { value: entry, selected: entry === goal.phase }, children: [entry] }),
      ),
    });
    const summary = h({ tag: "textarea", attrs: { id: `${controlId}-summary`, class: "input pe-text", rows: 2 } });
    summary.value = goal.summary;
    const change = (): void => commit({ ...goal, phase: phase.value, summary: summary.value });
    phase.addEventListener("change", change);
    summary.addEventListener("change", change);
    return [
      h({
        tag: "div",
        attrs: { class: "pe-sub" },
        children: [h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-phase` }, children: ["届けるフェーズ"] }), phase],
      }),
      h({
        tag: "div",
        attrs: { class: "pe-sub" },
        children: [h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-summary` }, children: ["ゴールの中身"] }), summary],
      }),
      h({
        tag: "div",
        attrs: { class: "pe-sub" },
        children: [
          h({ tag: "span", attrs: { class: "pe-sub-label" }, children: ["納品物"] }),
          h({
            tag: "ul",
            attrs: { class: "pe-rowsx" },
            children: goal.deliverables.map((entry) =>
              h({
                tag: "li",
                children: [entry.doc === undefined ? null : h({ tag: "span", attrs: { class: "mono" }, children: [entry.doc] }), entry.doc === undefined ? null : " ", entry.title],
              }),
            ),
          }),
        ],
      }),
    ];
  }

  /** 対象・カテゴリー・関連する場所（1 行ずつの表）。行の名前を書き換えたら古い名前 → 新しい名前の対応を付け、使われている行を消したら付け替え先を選ばせる */
  function tableInputs({
    props,
    key,
    controlId,
    commit,
  }: {
    props: WorkspaceSettingsProps;
    key: keyof typeof TABLES;
    controlId: string;
    commit: (next: unknown, map?: Record<string, string | null>) => void;
  }): HTMLElement[] {
    const { label, columns } = TABLES[key];
    const rows = ((props.settings as unknown as Record<string, unknown>)[key] ?? []) as Record<string, string>[];
    const wrap = h({ tag: "div", attrs: { class: "pe-mini-wrap" } });
    const holder = h({ tag: "div", attrs: { class: "pe-moves" } });
    const body = h({ tag: "tbody" });
    rows.forEach((row, at) => {
      const cells = columns.map((column) => {
        const input = h({
          tag: "input",
          attrs: {
            id: `${controlId}-${at}-${column.key}`,
            class: "input",
            type: column.type,
            value: row[column.key] ?? "",
            "aria-label": `${at + 1} 行目の${column.title}`,
          },
        });
        input.addEventListener("change", () => {
          const next = rows.map((entry, position) => (position === at ? { ...entry, [column.key]: input.value } : entry));
          // 対象・カテゴリーの名前を書き換えた: 古い名前 → 新しい名前の対応を付ける
          const renamed = column.key === "name" && (key === "targets" || key === "categories") && row["name"] !== input.value;
          commit(next, renamed ? { [row["name"] ?? ""]: input.value } : undefined);
        });
        return h({ tag: "td", children: [input] });
      });
      const remove = h({
        tag: "button",
        attrs: {
          class: "icon-btn",
          type: "button",
          "aria-label": `${at + 1} 行目を削除`,
          onclick: () => {
            const next = rows.filter((_, position) => position !== at);
            const used =
              key === "links"
                ? 0
                : usageCount({ index: props.index, threads: props.threads ?? [], key, value: row["name"] ?? "" });
            if (used === 0) {
              commit(next);
              return;
            }
            // 使われている行を消した: 付け替え先を選んだときに、対応つきで溜める
            const removed = row["name"] ?? "";
            holder.querySelector(`[data-moving="${removed}"]`)?.remove();
            holder.append(
              moveSelect({
                key: key as UsedSettingKey,
                removed,
                count: used,
                next,
                done: (target) => commit(next, { [removed]: target }),
              }),
            );
          },
        },
        children: [icon("trash")],
      });
      body.append(h({ tag: "tr", children: [...cells, h({ tag: "td", children: [remove] })] }));
    });
    wrap.append(
      h({
        tag: "table",
        attrs: { class: "pe-mini", "aria-labelledby": `${controlId}-label` },
        children: [
          h({
            tag: "thead",
            children: [
              h({
                tag: "tr",
                children: [
                  ...columns.map((column) => h({ tag: "th", attrs: { scope: "col" }, children: [column.title] })),
                  h({ tag: "th", children: [h({ tag: "span", attrs: { class: "sr-only" }, children: ["操作"] })] }),
                ],
              }),
            ],
          }),
          body,
        ],
      }),
    );
    return [
      wrap,
      holder,
      h({
        tag: "button",
        attrs: {
          class: "btn pe-row-add",
          type: "button",
          onclick: () => commit([...rows, Object.fromEntries(columns.map((column) => [column.key, ""]))]),
        },
        children: [icon("plus"), `${label}を追加`],
      }),
    ];
  }
}
