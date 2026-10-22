"use strict";
// 設定の画面。ワークスペースの設定を、キーごとの入力で書き換える別の画面。
var MindmapPreview;
(function (MindmapPreview) {
    /** 1 行ずつの表で書き換える設定のキーと、列 */
    const TABLES = {
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
    const GROUPS = [
        { title: "話し合い", keys: ["summary", "description", "playbooks", "goal"] },
        { title: "進め方", keys: ["phases", "target_label", "targets", "categories"] },
        { title: "タグと関連", keys: ["tags", "links"] },
        { title: "変更履歴", keys: ["history_limit"] },
    ];
    /** 設定のキーの入力欄の名前 */
    const SETTING_NAMES = {
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
    function usageCount({ index, threads, key, value, }) {
        let count = 0;
        for (const { item } of index.byId.values()) {
            if (key === "phases" && item.phase === value)
                count += 1;
            if (key === "targets" && item.target === value)
                count += 1;
            if (key === "categories" && item.category === value)
                count += 1;
            if (key === "tags" && (item.tags ?? []).includes(value))
                count += 1;
        }
        if (key === "targets")
            count += index.data.settings.categories.filter((category) => category.target === value).length;
        if (key === "tags")
            count += threads.filter((thread) => thread.tags.includes(value)).length;
        return count;
    }
    MindmapPreview.usageCount = usageCount;
    /** 設定の画面（見出しの帯と、まとまりごとの入力）を返す */
    function workspaceSettings(props) {
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "pe-form pe-ws-form",
                novalidate: true,
                "aria-label": "ワークスペースの設定",
                onsubmit: (event) => event.preventDefault(),
            },
            children: GROUPS.map((group) => MindmapPreview.h({
                tag: "fieldset",
                attrs: { class: "pe-ws-group" },
                children: [MindmapPreview.h({ tag: "legend", children: [group.title] }), ...group.keys.map((key) => settingField({ props, key }))],
            })),
        });
        form.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
        return MindmapPreview.h({
            tag: "main",
            attrs: { class: "content pe-ws pe-screen" },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "pe-screen-head" },
                    children: [
                        MindmapPreview.h({ tag: "h1", attrs: { tabindex: "-1" }, children: ["設定"] }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn", type: "button", onclick: () => props.on.close() },
                            children: [MindmapPreview.icon("x"), "閉じる"],
                        }),
                    ],
                }),
                form,
            ],
        });
    }
    MindmapPreview.workspaceSettings = workspaceSettings;
    /** 設定のキー 1 つの入力欄（名前の行・入力・誤り） */
    function settingField({ props, key }) {
        const { settings, marks, errors, on } = props;
        const name = SETTING_NAMES[key] ?? key;
        const controlId = `pe-ws-${key}`;
        const mark = marks[key];
        const wrap = MindmapPreview.h({
            tag: "div",
            attrs: {
                class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}`,
                "data-key": key,
            },
        });
        const record = settings;
        const value = record[key];
        wrap.append(MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-label-row" },
            children: [
                key === "goal" || key in TABLES || key === "playbooks" || key === "phases" || key === "tags"
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-label", id: `${controlId}-label` }, children: [name] })
                    : MindmapPreview.h({ tag: "label", attrs: { for: controlId, id: `${controlId}-label` }, children: [name] }),
                mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
            ],
        }));
        /** 設定のキーを溜める */
        const commit = (next, map) => on.change(map === undefined ? { key, value: next } : { key, value: next, map });
        if (key === "summary" || key === "target_label") {
            const input = MindmapPreview.h({
                tag: "input",
                attrs: { id: controlId, class: "input", type: "text", value: typeof value === "string" ? value : "", autocomplete: "off" },
            });
            input.addEventListener("change", () => commit(input.value));
            wrap.append(input);
        }
        else if (key === "description") {
            const area = MindmapPreview.h({ tag: "textarea", attrs: { id: controlId, class: "input pe-text", rows: 2 } });
            area.value = typeof value === "string" ? value : "";
            // 空にして離れたら、説明を消す
            area.addEventListener("change", () => commit(area.value === "" ? null : area.value));
            wrap.append(area);
        }
        else if (key === "history_limit") {
            const input = MindmapPreview.h({
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
                if (input.value.trim() === "" || !Number.isInteger(next) || next < 1)
                    return;
                commit(next);
            });
            wrap.append(input, MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint" }, children: ["変更履歴に残す書き換えのまとまりの数"] }));
        }
        else if (key === "playbooks" || key === "phases" || key === "tags") {
            // タグの語彙は名前と説明のオブジェクトの並びなので、チップには名前を出す
            const names = key === "tags" ? (settings.tags ?? []).map((tag) => tag.name) : Array.isArray(value) ? value : [];
            wrap.append(chipsSetting({ props, key, wrap, controlId, name, values: names, commit }));
        }
        else if (key === "goal") {
            wrap.append(...goalInputs({ props, controlId, commit }));
        }
        else if (key in TABLES) {
            wrap.append(...tableInputs({ props, key: key, controlId, commit }));
        }
        const failure = errors[key];
        if (failure !== undefined) {
            wrap.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return wrap;
    }
    /** 使われている値を外したときの付け替え先の選択（選ぶまで溜めない） */
    function moveSelect({ key, removed, count, next, done, }) {
        const remaining = (Array.isArray(next) ? next : []).map((entry) => typeof entry === "string" ? entry : String(entry.name));
        const id = `pe-ws-${key}-move-${MindmapPreview.safeId(removed)}`;
        const select = MindmapPreview.h({
            tag: "select",
            attrs: { id, class: "input" },
            children: [
                MindmapPreview.h({ tag: "option", attrs: { value: "", selected: true }, children: ["選んでください"] }),
                ...remaining.map((entry) => MindmapPreview.h({ tag: "option", attrs: { value: entry }, children: [entry] })),
                key === "tags" ? MindmapPreview.h({ tag: "option", attrs: { value: DROP_TAG }, children: [DROP_TAG] }) : null,
            ],
        });
        select.addEventListener("change", () => {
            if (select.value === "")
                return;
            done(select.value === DROP_TAG ? null : select.value);
        });
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-sub pe-move", "data-moving": removed },
            children: [
                MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: id }, children: [`${removed} を使っている ${count} 件の付け替え先`] }),
                select,
                MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint" }, children: [MindmapPreview.icon("alert"), "付け替え先を選ぶと保存待ちに入ります。"] }),
            ],
        });
    }
    /** プレイブック・フェーズ・タグの語彙（チップ）。使われているフェーズ・タグを外したときは付け替え先を選ばせる */
    function chipsSetting({ props, key, wrap, controlId, name, values, commit, }) {
        const box = MindmapPreview.h({ tag: "div", attrs: { class: "pe-chips-set" } });
        box.append(MindmapPreview.chipsInput({
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
                const used = removed !== null && key !== "playbooks"
                    ? usageCount({ index: props.index, threads: props.threads ?? [], key, value: removed })
                    : 0;
                if (removed === null || used === 0) {
                    commit(next);
                    return;
                }
                // 使われている値を外した: 付け替え先を選んだときに、対応つきで溜める
                wrap.querySelector(`[data-moving="${removed}"]`)?.remove();
                wrap.append(moveSelect({
                    key: key,
                    removed,
                    count: used,
                    next,
                    done: (target) => commit(next, { [removed]: target }),
                }));
            },
        }));
        return box;
    }
    /** ゴール（届けるフェーズ・ゴールの中身を書き換え、納品物は読むだけで並べる） */
    function goalInputs({ props, controlId, commit, }) {
        const { settings } = props;
        const goal = settings.goal ?? { phase: settings.phases[0] ?? "", summary: "", deliverables: [] };
        const phase = MindmapPreview.h({
            tag: "select",
            attrs: { id: `${controlId}-phase`, class: "input" },
            children: settings.phases.map((entry) => MindmapPreview.h({ tag: "option", attrs: { value: entry, selected: entry === goal.phase }, children: [entry] })),
        });
        const summary = MindmapPreview.h({ tag: "textarea", attrs: { id: `${controlId}-summary`, class: "input pe-text", rows: 2 } });
        summary.value = goal.summary;
        const change = () => commit({ ...goal, phase: phase.value, summary: summary.value });
        phase.addEventListener("change", change);
        summary.addEventListener("change", change);
        return [
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-phase` }, children: ["届けるフェーズ"] }), phase],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [MindmapPreview.h({ tag: "label", attrs: { class: "pe-sub-label", for: `${controlId}-summary` }, children: ["ゴールの中身"] }), summary],
            }),
            MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-sub" },
                children: [
                    MindmapPreview.h({ tag: "span", attrs: { class: "pe-sub-label" }, children: ["納品物"] }),
                    MindmapPreview.h({
                        tag: "ul",
                        attrs: { class: "pe-rowsx" },
                        children: goal.deliverables.map((entry) => MindmapPreview.h({
                            tag: "li",
                            children: [entry.doc === undefined ? null : MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [entry.doc] }), entry.doc === undefined ? null : " ", entry.title],
                        })),
                    }),
                ],
            }),
        ];
    }
    /** 対象・カテゴリー・関連する場所（1 行ずつの表）。行の名前を書き換えたら古い名前 → 新しい名前の対応を付け、使われている行を消したら付け替え先を選ばせる */
    function tableInputs({ props, key, controlId, commit, }) {
        const { label, columns } = TABLES[key];
        const rows = (props.settings[key] ?? []);
        const wrap = MindmapPreview.h({ tag: "div", attrs: { class: "pe-mini-wrap" } });
        const holder = MindmapPreview.h({ tag: "div", attrs: { class: "pe-moves" } });
        const body = MindmapPreview.h({ tag: "tbody" });
        rows.forEach((row, at) => {
            const cells = columns.map((column) => {
                const input = MindmapPreview.h({
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
                return MindmapPreview.h({ tag: "td", children: [input] });
            });
            const remove = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "icon-btn",
                    type: "button",
                    "aria-label": `${at + 1} 行目を削除`,
                    onclick: () => {
                        const next = rows.filter((_, position) => position !== at);
                        const used = key === "links"
                            ? 0
                            : usageCount({ index: props.index, threads: props.threads ?? [], key, value: row["name"] ?? "" });
                        if (used === 0) {
                            commit(next);
                            return;
                        }
                        // 使われている行を消した: 付け替え先を選んだときに、対応つきで溜める
                        const removed = row["name"] ?? "";
                        holder.querySelector(`[data-moving="${removed}"]`)?.remove();
                        holder.append(moveSelect({
                            key: key,
                            removed,
                            count: used,
                            next,
                            done: (target) => commit(next, { [removed]: target }),
                        }));
                    },
                },
                children: [MindmapPreview.icon("trash")],
            });
            body.append(MindmapPreview.h({ tag: "tr", children: [...cells, MindmapPreview.h({ tag: "td", children: [remove] })] }));
        });
        wrap.append(MindmapPreview.h({
            tag: "table",
            attrs: { class: "pe-mini", "aria-labelledby": `${controlId}-label` },
            children: [
                MindmapPreview.h({
                    tag: "thead",
                    children: [
                        MindmapPreview.h({
                            tag: "tr",
                            children: [
                                ...columns.map((column) => MindmapPreview.h({ tag: "th", attrs: { scope: "col" }, children: [column.title] })),
                                MindmapPreview.h({ tag: "th", children: [MindmapPreview.h({ tag: "span", attrs: { class: "sr-only" }, children: ["操作"] })] }),
                            ],
                        }),
                    ],
                }),
                body,
            ],
        }));
        return [
            wrap,
            holder,
            MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "btn pe-row-add",
                    type: "button",
                    onclick: () => commit([...rows, Object.fromEntries(columns.map((column) => [column.key, ""]))]),
                },
                children: [MindmapPreview.icon("plus"), `${label}を追加`],
            }),
        ];
    }
})(MindmapPreview || (MindmapPreview = {}));
