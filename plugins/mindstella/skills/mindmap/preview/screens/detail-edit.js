"use strict";
// 詳細パネル・詳細の全画面の編集の表示。キーごとの入力と、検討事項の案の入力、項目の削除。
var MindmapPreview;
(function (MindmapPreview) {
    /** 種類ごとに編集の表示へ並べるキー（読む表示と同じ順） */
    const EDITABLE_KEYS = {
        decisions: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "target", input: "select" },
            { key: "category", input: "select" },
            { key: "phase", input: "select" },
            { key: "tags", input: "tags" },
            { key: "depends_on", input: "refs" },
            { key: "options", input: "options" },
            { key: "answer", input: "textarea" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        tasks: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "target", input: "select" },
            { key: "kind", input: "select" },
            { key: "tags", input: "tags" },
            { key: "result", input: "textarea" },
            { key: "body", input: "body" },
        ],
        research: [
            { key: "title", input: "text" },
            { key: "question", input: "textarea" },
            { key: "conclusion", input: "textarea" },
            { key: "confidence", input: "select" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        docs: [
            { key: "status", input: "select" },
            { key: "title", input: "text" },
            { key: "kind", input: "text" },
            { key: "deliverable", input: "check" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        terms: [
            { key: "title", input: "text" },
            { key: "meaning", input: "textarea" },
            { key: "aliases", input: "refs" },
            { key: "tags", input: "tags" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        notes: [
            { key: "title", input: "text" },
            { key: "content", input: "textarea" },
            { key: "tags", input: "tags" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
        logs: [
            { key: "title", input: "text" },
            { key: "date", input: "text" },
            { key: "related", input: "refs" },
            { key: "withdrawn", input: "check" },
            { key: "reason", input: "textarea" },
            { key: "body", input: "body" },
        ],
    };
    /** 項目を追加する入力に並べるキー（スキーマで必須のキーと、状態・タグ・本文。検討事項は案も） */
    const ADD_KEYS = {
        decisions: ["status", "title", "options", "tags", "body"],
        tasks: ["status", "title", "kind", "tags", "body"],
        research: ["title", "question", "tags", "body"],
        docs: ["status", "title", "kind", "deliverable", "tags", "body"],
        terms: ["title", "meaning", "tags", "body"],
        notes: ["title", "content", "tags", "body"],
        logs: ["title", "date", "body"],
    };
    /** 追加する項目の最初の値（スキーマで必須のキーを、保存で弾かれない値で埋める） */
    function addDefaults({ kind, today }) {
        switch (kind) {
            case "decisions":
                return { status: "未整理" };
            case "tasks":
                return { status: "未着手", kind: "作業" };
            case "research":
                return { question: "" };
            case "docs":
                return { status: "下書き", kind: "文書", deliverable: false, body: "" };
            case "terms":
                return { meaning: "" };
            case "notes":
                return { content: "" };
            case "logs":
                return { date: today };
        }
    }
    MindmapPreview.addDefaults = addDefaults;
    /** タスクの種類の選択肢 */
    const TASK_KINDS = ["作業", "調査", "検証"];
    /** 調査の確からしさの選択肢 */
    const CONFIDENCES = ["高", "中", "低"];
    /** 空にできない文字のキー（空のときは溜めず、誤りを出す） */
    const REQUIRED_TEXT_KEYS = new Set(["title"]);
    /** 値を並べるキーの入力欄に出す案内 */
    const CHIP_HINTS = {
        tags: "タグを入れる",
        depends_on: "ID を入れる",
        related: "ID を入れる",
        aliases: "別名を入れる",
    };
    /** 種類ごとに編集の表示へ並べるキーと入力の種類（`id`・`created`・`updated` は含めない） */
    function editableKeys(kind) {
        return EDITABLE_KEYS[kind].map((entry) => ({ ...entry }));
    }
    MindmapPreview.editableKeys = editableKeys;
    /** キーの呼び名（用語のタイトルは「用語」、取り下げる項目の理由は「取り下げた理由」） */
    function labelOf({ kind, key }) {
        if (key === "title" && kind === "terms")
            return "用語";
        if (key === "reason" && kind !== "decisions" && kind !== "tasks")
            return "取り下げた理由";
        return MindmapPreview.KEY_LABELS[key] ?? key;
    }
    /** 要素の id に使えない文字を外す */
    function safeId(text) {
        return text.replace(/[^A-Za-z0-9]/g, "");
    }
    MindmapPreview.safeId = safeId;
    /** 書き込めない理由（警告の印と文言）。`changed` は AI が書き換えた日時を添える */
    function blockedNote({ blocked, updated, onOpen, }) {
        if (blocked.reason === "changed") {
            const when = updated === null ? "" : `${MindmapPreview.formatJst(updated)} `;
            return MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-blocked-note" },
                children: [MindmapPreview.icon("alert"), `溜めた後の ${when}に AI がこの項目を書き換えたため、書き込めません。取り消してから入れ直してください。`],
            });
        }
        if (blocked.reason === "referenced" && blocked.refs.length > 0) {
            const refs = blocked.refs.flatMap((ref, position) => [
                position > 0 ? "・" : null,
                onOpen === undefined
                    ? MindmapPreview.h({ tag: "span", attrs: { class: "mono" }, children: [ref] })
                    : MindmapPreview.h({ tag: "button", attrs: { class: "idlink", type: "button", onclick: () => onOpen(ref) }, children: [ref] }),
            ]);
            return MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-blocked-note" },
                children: [MindmapPreview.icon("alert"), ...refs, " が指しているため削除できません。指している項目から外してください。"],
            });
        }
        return MindmapPreview.h({ tag: "p", attrs: { class: "pe-blocked-note" }, children: [MindmapPreview.icon("alert"), blocked.detail] });
    }
    MindmapPreview.blockedNote = blockedNote;
    /** 項目とスレッドが使っているタグを、サーバーの `normalize_tag` と同じく NFKC と小文字にそろえ、重なりを除いて件数の多い順（同じ件数は名前の順）に並べる */
    function usedTags({ index, threads }) {
        const counts = new Map();
        /** 1 つの項目かスレッドの `tags` を数える（同じタグを表記を変えて 2 回持っても 1 件） */
        const count = (tags) => {
            for (const name of new Set(tags.map((tag) => tag.normalize("NFKC").toLowerCase()))) {
                counts.set(name, (counts.get(name) ?? 0) + 1);
            }
        };
        for (const { item } of index.byId.values())
            count(item.tags ?? []);
        for (const thread of threads)
            count(thread.tags);
        return [...counts.keys()].sort((left, right) => (counts.get(right) ?? 0) - (counts.get(left) ?? 0) || (left < right ? -1 : left > right ? 1 : 0));
    }
    MindmapPreview.usedTags = usedTags;
    /** 編集の表示（`form`）を返す。入力欄を離れたとき（選ぶ・チェックは選んだとき）に `on.change` で溜める編集を知らせる */
    function detailEditForm(props) {
        const { kind, item, removing, on } = props;
        const adding = item.id.startsWith(MindmapPreview.NEW_ID_PREFIX);
        const keys = adding
            ? EDITABLE_KEYS[kind].filter((entry) => ADD_KEYS[kind].includes(entry.key))
            : EDITABLE_KEYS[kind];
        const form = MindmapPreview.h({
            tag: "form",
            attrs: {
                class: "pe-form",
                "data-id": item.id,
                novalidate: true,
                "aria-label": adding ? `${MindmapPreview.KIND_LABEL[kind]}を追加` : `${item.id} を編集`,
                onsubmit: (event) => event.preventDefault(),
            },
        });
        if (removing) {
            form.append(MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-hint", role: "status" },
                children: [MindmapPreview.icon("trash"), "削除を溜めています。削除を取り消すと編集できます。"],
            }));
        }
        // 編集できないキー（ID・作成・更新・編集した人）
        form.append(MindmapPreview.h({
            tag: "dl",
            attrs: { class: "pe-fixed" },
            children: [
                MindmapPreview.h({ tag: "dt", children: ["ID"] }),
                MindmapPreview.h({ tag: "dd", attrs: { class: "mono" }, children: [adding ? "保存で決まる" : item.id] }),
                ...(adding
                    ? []
                    : [
                        MindmapPreview.h({ tag: "dt", children: ["作成"] }),
                        MindmapPreview.h({ tag: "dd", children: [MindmapPreview.formatJst(item.created)] }),
                        MindmapPreview.h({ tag: "dt", children: ["更新"] }),
                        MindmapPreview.h({
                            tag: "dd",
                            children: [`${MindmapPreview.formatJst(item.updated)}（${item.updated_by === "user" ? "利用者" : "AI"}）`],
                        }),
                    ]),
            ],
        }));
        for (const { key, input } of keys) {
            form.append(input === "options" ? optionsField(props) : keyField({ props, key, input }));
        }
        if (!adding)
            form.append(removeSection(props));
        // 溜めた知らせ（読み上げにも伝える。使う側が文言を入れる）
        form.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-form-msg", role: "status" } }));
        return form;
    }
    MindmapPreview.detailEditForm = detailEditForm;
    /** キーの名前の行（名前と、必須の印・保存待ちの印） */
    function labelRow({ props, key, controlId, name, }) {
        const mark = props.marks[key];
        const required = REQUIRED_TEXT_KEYS.has(key);
        return MindmapPreview.h({
            tag: "div",
            attrs: { class: "pe-label-row" },
            children: [
                MindmapPreview.h({
                    tag: "label",
                    attrs: { for: controlId },
                    children: [name, required ? MindmapPreview.h({ tag: "span", attrs: { class: "pe-req" }, children: ["必須"] }) : null],
                }),
                mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
            ],
        });
    }
    /** キー 1 つの入力欄 */
    function keyField({ props, key, input, }) {
        const { kind, item, settings, removing, on } = props;
        const controlId = `pe-${safeId(item.id)}-${key}`;
        const name = labelOf({ kind, key });
        const mark = props.marks[key];
        const wrap = MindmapPreview.h({
            tag: "div",
            attrs: {
                class: `pe-field${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}${input === "check" ? " pe-check" : ""}`,
                "data-key": key,
            },
        });
        const record = item;
        const value = key === "body" ? (props.body ?? "") : record[key];
        let control;
        /** キーの編集を知らせる。空のタイトルは溜めず、失敗の赤の枠と誤りを出す */
        const commit = (next) => {
            if (key === "title") {
                const empty = typeof next !== "string" || next.trim() === "";
                if (empty)
                    control.setAttribute("aria-invalid", "true");
                else
                    control.removeAttribute("aria-invalid");
                wrap.classList.toggle("is-invalid", empty);
                if (empty)
                    return;
            }
            on.change({ op: "set", key, value: next });
        };
        if (input === "select") {
            const options = selectOptions({ kind, key, settings });
            const optional = !(key === "status" || key === "kind");
            const select = MindmapPreview.h({
                tag: "select",
                attrs: { id: controlId, name: key, class: "input", disabled: removing },
                children: [
                    optional ? MindmapPreview.h({ tag: "option", attrs: { value: "", selected: value === undefined || value === null }, children: ["（なし）"] }) : null,
                    ...options.map((option) => MindmapPreview.h({ tag: "option", attrs: { value: option, selected: option === value }, children: [option] })),
                ],
            });
            select.addEventListener("change", () => commit(select.value === "" ? null : select.value));
            control = select;
        }
        else if (input === "check") {
            const box = MindmapPreview.h({
                tag: "input",
                attrs: { id: controlId, name: key, type: "checkbox", checked: value === true, disabled: removing },
            });
            box.addEventListener("change", () => commit(box.checked));
            control = box;
        }
        else if (input === "tags" || input === "refs") {
            control = chipsInput({
                controlId,
                name,
                hint: CHIP_HINTS[key] ?? `${name}を入れる`,
                values: Array.isArray(value) ? value : [],
                suggestions: key === "tags" ? props.usedTags : null,
                monospace: key !== "tags",
                disabled: removing,
                onChange: (next) => commit(next),
            });
        }
        else if (input === "textarea" || input === "body") {
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: controlId,
                    name: key,
                    class: `input pe-text${input === "body" ? " pe-body" : ""}`,
                    rows: input === "body" ? 8 : 3,
                    disabled: removing,
                },
            });
            area.value = typeof value === "string" ? value : "";
            area.addEventListener("change", () => {
                // 本文は空の文字列で書く。そのほかは空にして離れたらキーを消す
                commit(area.value === "" && input !== "body" ? null : area.value);
            });
            control = area;
        }
        else {
            const text = MindmapPreview.h({
                tag: "input",
                attrs: {
                    id: controlId,
                    name: key,
                    class: "input",
                    type: key === "date" ? "date" : "text",
                    value: typeof value === "string" ? value : "",
                    autocomplete: "off",
                    disabled: removing,
                },
            });
            text.addEventListener("change", () => commit(text.value === "" && !REQUIRED_TEXT_KEYS.has(key) ? null : text.value));
            control = text;
        }
        wrap.append(labelRow({ props, key, controlId, name }));
        if (key === "title") {
            // 空のタイトルは溜めず、離れたときに失敗の赤の枠と誤りを出す
            const errorId = `${controlId}-error`;
            const error = MindmapPreview.h({
                tag: "p",
                attrs: { class: "pe-error", id: errorId },
                children: [MindmapPreview.icon("alert"), "タイトルを書いてください。"],
            });
            control.setAttribute("required", "");
            control.setAttribute("aria-describedby", errorId);
            // 追加の入力を開いたとき、最初にフォーカスを置く入力欄
            control.setAttribute("data-first", "");
            wrap.append(control, error);
        }
        else {
            wrap.append(control);
        }
        const blocked = props.blocked[key];
        if (blocked !== undefined)
            wrap.append(blockedNote({ blocked, updated: item.updated }));
        const failure = props.errors[key];
        if (failure !== undefined) {
            wrap.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return wrap;
    }
    /** 選ぶキーの選択肢 */
    function selectOptions({ kind, key, settings }) {
        switch (key) {
            case "status":
                return kind === "decisions" ? MindmapPreview.DECISION_STATUSES : kind === "tasks" ? MindmapPreview.TASK_STATUSES : MindmapPreview.DOC_STATUSES;
            case "kind":
                return TASK_KINDS;
            case "confidence":
                return CONFIDENCES;
            case "target":
                return settings.targets.map((target) => target.name);
            case "category":
                return settings.categories.map((category) => category.name);
            default:
                return settings.phases;
        }
    }
    /** 値を並べるキーの入力（チップと、足す入力欄）。値の並びを変えるたびに `onChange` で新しい並びを知らせる（チップを外したときは外した値も） */
    function chipsInput({ controlId, name, hint, values, suggestions, monospace, disabled, onChange, }) {
        let current = [...values];
        const box = MindmapPreview.h({ tag: "div", attrs: { class: "pe-chips", role: "group", "aria-label": name } });
        const listId = `${controlId}-list`;
        const field = MindmapPreview.h({
            tag: "input",
            attrs: {
                id: controlId,
                class: "input pe-chip-input",
                type: "text",
                list: suggestions === null ? null : listId,
                placeholder: hint,
                "aria-label": `${name}を追加`,
                autocomplete: "off",
                disabled,
            },
        });
        /** 入力した値を並びに足す（空と、もうある値は足さない） */
        const addValue = () => {
            const text = field.value.trim();
            field.value = "";
            if (text === "" || current.includes(text))
                return;
            current = [...current, text];
            draw();
            onChange(current, null);
            box.querySelector(".pe-chip-input")?.focus();
        };
        field.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" || event.isComposing)
                return;
            event.preventDefault();
            addValue();
        });
        field.addEventListener("change", addValue);
        /** チップを描き直す */
        const draw = () => {
            box.replaceChildren(...current.map((entry) => MindmapPreview.h({
                tag: "span",
                attrs: { class: `tag pe-chip${monospace ? " mono" : ""}` },
                children: [
                    entry,
                    MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "pe-chip-x",
                            type: "button",
                            "aria-label": `${entry} を外す`,
                            disabled,
                            onclick: () => {
                                current = current.filter((other) => other !== entry);
                                draw();
                                onChange(current, entry);
                            },
                        },
                        children: [MindmapPreview.icon("x")],
                    }),
                ],
            })), field, ...(suggestions === null
                ? []
                : [
                    MindmapPreview.h({
                        tag: "datalist",
                        attrs: { id: listId },
                        children: suggestions.map((tag) => MindmapPreview.h({ tag: "option", attrs: { value: tag } })),
                    }),
                ]));
        };
        draw();
        return box;
    }
    MindmapPreview.chipsInput = chipsInput;
    /** 検討事項の案（1 案 1 枚。中身の書き換え・採用する案の切り替え・削除と、案を足す） */
    function optionsField(props) {
        const { item, removing, removedOptions, on } = props;
        const section = MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "pe-field pe-options", "data-key": "options" },
            children: [MindmapPreview.h({ tag: "legend", children: ["案"] })],
        });
        const idPart = safeId(item.id);
        const options = item.options ?? [];
        // 追加の入力では、採用している案は削除できない（採用をほかの案へ移すと削除できる）
        const adding = item.id.startsWith(MindmapPreview.NEW_ID_PREFIX);
        for (const option of options) {
            const removed = removedOptions.includes(option.key);
            const mark = props.marks[option.key];
            const textId = `pe-${idPart}-opt-${option.key}`;
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: textId,
                    class: "input pe-text",
                    rows: 2,
                    "aria-label": `案 ${option.key} の中身`,
                    disabled: removing || removed,
                },
            });
            area.value = option.content;
            area.addEventListener("change", () => on.change({ op: "option-edit", key: option.key, value: { content: area.value } }));
            const blocked = props.blocked[option.key];
            section.append(MindmapPreview.h({
                tag: "div",
                attrs: {
                    class: `pe-opt${mark === "pending" ? " is-pending" : ""}${mark === "blocked" ? " is-blocked" : ""}${removed ? " is-removed" : ""}`,
                    "data-key": option.key,
                },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "pe-opt-head" },
                        children: [
                            MindmapPreview.h({ tag: "span", attrs: { class: "key", "aria-hidden": "true" }, children: [option.key] }),
                            MindmapPreview.h({
                                tag: "label",
                                attrs: { class: "pe-adopt" },
                                children: [
                                    MindmapPreview.h({
                                        tag: "input",
                                        attrs: {
                                            id: `pe-${idPart}-adopt-${option.key}`,
                                            type: "radio",
                                            name: `${item.id}-adopt`,
                                            value: option.key,
                                            checked: option.adopted === true,
                                            disabled: removing || removed,
                                            onchange: () => on.change({ op: "adopt", key: option.key, value: option.key }),
                                        },
                                    }),
                                    "採用",
                                ],
                            }),
                            mark === undefined ? null : MindmapPreview.pendingEditMark({ kind: mark, compact: true }),
                            MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                            removed || (adding && option.adopted === true)
                                ? null
                                : MindmapPreview.h({
                                    tag: "button",
                                    attrs: {
                                        class: "icon-btn",
                                        type: "button",
                                        "aria-label": `案 ${option.key} を削除`,
                                        title: `案 ${option.key} を削除`,
                                        disabled: removing,
                                        onclick: () => on.change({ op: "option-remove", key: option.key, value: null }),
                                    },
                                    children: [MindmapPreview.icon("trash")],
                                }),
                        ],
                    }),
                    area,
                    blocked === undefined ? null : blockedNote({ blocked, updated: item.updated }),
                ],
            }));
        }
        // 書きかけの案（項目の案に同じ記号が載ったものは描かない）
        const drafts = props.optionDrafts.filter((draft) => !options.some((option) => option.key === draft.key));
        for (const draft of drafts) {
            const area = MindmapPreview.h({
                tag: "textarea",
                attrs: {
                    id: `pe-${idPart}-opt-${draft.key}`,
                    class: "input pe-text",
                    rows: 2,
                    "aria-label": `案 ${draft.key} の中身`,
                    disabled: removing,
                },
            });
            area.value = draft.content;
            // 打つたびに書きかけを知らせ、空でない中身で離れたら溜める
            area.addEventListener("input", () => on.draft({ key: draft.key, content: area.value }));
            area.addEventListener("change", () => {
                if (area.value.trim() === "")
                    return;
                on.change({ op: "option-add", key: draft.key, value: { content: area.value } });
            });
            section.append(MindmapPreview.h({
                tag: "div",
                attrs: { class: "pe-opt", "data-key": draft.key, "data-draft": "" },
                children: [
                    MindmapPreview.h({
                        tag: "div",
                        attrs: { class: "pe-opt-head" },
                        children: [MindmapPreview.h({ tag: "span", attrs: { class: "key", "aria-hidden": "true" }, children: [draft.key] })],
                    }),
                    area,
                ],
            }));
        }
        const add = MindmapPreview.h({
            tag: "button",
            attrs: { class: "btn pe-opt-add", type: "button", disabled: removing },
            children: [MindmapPreview.icon("plus"), "案を追加"],
        });
        add.addEventListener("click", () => {
            // 次の記号（今ある案と、書きかけの案の記号の次）の空の書きかけを置く。描くのは使う側が状態から描き直したとき
            const symbols = [...options.map((option) => option.key), ...drafts.map((draft) => draft.key)];
            const next = String.fromCharCode(Math.max(64, ...symbols.map((symbol) => symbol.charCodeAt(0))) + 1);
            on.draft({ key: next, content: "" });
        });
        section.append(add);
        // 案の編集を溜められなかった理由は、案の入力の下にまとめて出す
        const failure = props.errors["options"];
        if (failure !== undefined) {
            section.append(MindmapPreview.h({ tag: "p", attrs: { class: "pe-hint", role: "alert" }, children: [MindmapPreview.icon("alert"), failure] }));
        }
        return section;
    }
    /** 項目を削除する区画（削除を溜める・取り消す。ほかの項目が指しているときは警告を出す） */
    function removeSection(props) {
        const { removing, referrers, on } = props;
        return MindmapPreview.h({
            tag: "section",
            attrs: { class: "pe-remove-sec" },
            children: [
                MindmapPreview.h({ tag: "h2", children: ["項目を削除"] }),
                removing
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn", type: "button", onclick: () => on.cancelRemove() },
                        children: [MindmapPreview.icon("undo"), "削除を取り消す"],
                    })
                    : MindmapPreview.h({
                        tag: "button",
                        attrs: { class: "btn pe-danger", type: "button", onclick: () => on.remove() },
                        children: [MindmapPreview.icon("trash"), "項目を削除"],
                    }),
                referrers.length === 0
                    ? null
                    : MindmapPreview.h({
                        tag: "p",
                        attrs: { class: "pe-hint" },
                        children: [
                            MindmapPreview.icon("alert"),
                            `${referrers.join("・")} が指しているため、保存のときに削除できません。指している項目から外すと削除できます。`,
                        ],
                    }),
            ],
        });
    }
})(MindmapPreview || (MindmapPreview = {}));
