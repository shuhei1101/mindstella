"use strict";
// 絞り込みのドロワー。条件ごとに値を件数つきのチェックボックスで並べ、タブの帯の下から左に重ねる非モーダルのパネルとして開く。
var MindmapPreview;
(function (MindmapPreview) {
    /** 次に描いたドロワーでフォーカスを移す先（操作した部品が描き直しで消えても、フォーカスを失わないために持つ） */
    let pendingFocus = null;
    /** 値のチェックボックスのうち、フォーカスを移す先を返す（見つからなければ最初の値） */
    function focusTargetOf({ drawer, focus }) {
        const inputs = [...drawer.querySelectorAll(".fd-body input[data-key]")];
        const found = focus.kind === "value"
            ? inputs.find((input) => input.dataset["key"] === focus.key && input.value === focus.value)
            : focus.kind === "group"
                ? inputs.find((input) => input.dataset["key"] === focus.key)
                : undefined;
        return found ?? inputs[0] ?? null;
    }
    /** 値の左に添える印（状態の印か、項目の種類の色の点） */
    function valueMark({ mark, value }) {
        if (mark === "status")
            return MindmapPreview.statusMark(value);
        if (mark !== "kind")
            return null;
        const kind = MindmapPreview.KIND_KEYS.find((key) => MindmapPreview.KIND_LABEL[key] === value);
        if (kind === undefined)
            return null;
        return MindmapPreview.h({ tag: "span", attrs: { class: "kdot", style: `background:var(${MindmapPreview.KIND_COLOR_VAR[kind]})` } });
    }
    /** 条件 1 つ（見出し・選んだ数と「解除」・値の並び） */
    function conditionGroup({ group, chosen, on }) {
        const values = group.values.map(({ value, count, hit }) => MindmapPreview.h({
            tag: "li",
            children: [
                MindmapPreview.h({
                    tag: "label",
                    attrs: { class: count === 0 ? "fd-opt zero" : "fd-opt" },
                    children: [
                        MindmapPreview.h({
                            tag: "input",
                            attrs: {
                                type: "checkbox",
                                value,
                                "data-key": group.key,
                                checked: chosen.includes(value),
                                onchange: (event) => {
                                    const checked = event.target.checked;
                                    pendingFocus = { kind: "value", key: group.key, value };
                                    on.select({ key: group.key, value, checked });
                                },
                            },
                        }),
                        valueMark({ mark: group.mark, value }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "fd-v" }, children: [value] }),
                        hit !== undefined && hit > 0
                            ? MindmapPreview.h({ tag: "span", attrs: { class: "hit-n", "aria-label": `キーワードに一致した項目 ${hit} 件` }, children: [hit] })
                            : null,
                        MindmapPreview.h({ tag: "span", attrs: { class: "n", "aria-label": `${count} 件` }, children: [count] }),
                    ],
                }),
            ],
        }));
        return MindmapPreview.h({
            tag: "fieldset",
            attrs: { class: "fd-group" },
            children: [
                MindmapPreview.h({
                    tag: "legend",
                    children: [
                        group.label,
                        chosen.length > 0 ? MindmapPreview.h({ tag: "span", attrs: { class: "fd-sel" }, children: [`${chosen.length} 件を選択`] }) : null,
                    ],
                }),
                chosen.length > 0
                    ? MindmapPreview.h({
                        tag: "button",
                        attrs: {
                            class: "btn ghost fd-clear",
                            type: "button",
                            "aria-label": `${group.label}の条件を解除`,
                            onclick: () => {
                                pendingFocus = { kind: "group", key: group.key };
                                on.clear(group.key);
                            },
                        },
                        children: ["解除"],
                    })
                    : null,
                MindmapPreview.h({ tag: "ul", attrs: { class: "fd-opts" }, children: values }),
            ],
        });
    }
    /** ドロワーの操作（値の選択・条件の解除・すべて解除）を、新しい条件を `onFilter` に渡す形にする */
    function drawerCallbacks({ filters, onFilter, onClose, }) {
        return {
            select: ({ key, value, checked }) => {
                const current = filters[key] ?? [];
                const next = checked ? [...current, value] : current.filter((candidate) => candidate !== value);
                onFilter(next.length === 0 ? MindmapPreview.withoutKey(filters, key) : { ...filters, [key]: next });
            },
            clear: (key) => onFilter(MindmapPreview.withoutKey(filters, key)),
            clearAll: () => onFilter({}),
            close: onClose,
        };
    }
    /** 絞り込みのドロワーの狭い幅の境（これ以下はトップバーの下から全幅で重ねる） */
    const DRAWER_NARROW_QUERY = "(max-width: 900px)";
    /** 画面が持つ条件と絞り込みの結果から、ドロワーを組む（開いていなければ null）。キーワードに一致した件数を添える画面は `hit` を渡す */
    function screenDrawer({ drawerOpen, rows, columns, filters, shown, hit, onFilter, onClose, }) {
        if (!drawerOpen)
            return null;
        return filterDrawer({
            groups: MindmapPreview.drawerGroups({ rows, columns, filters, ...(hit === undefined ? {} : { hit }) }),
            selected: filters,
            total: rows.length,
            shown,
            narrow: matchMedia(DRAWER_NARROW_QUERY).matches,
            on: drawerCallbacks({ filters, onFilter, onClose }),
        });
    }
    MindmapPreview.screenDrawer = screenDrawer;
    /** 絞り込みのドロワーを返す。文書に入った後に非モーダルで開き、描き直しても中のスクロールの位置と押した値へのフォーカスを保つ */
    function filterDrawer({ groups, selected, total, shown, narrow, on }) {
        // 描き直す前のドロワー（あれば、スクロールの位置とフォーカスを引き継ぐ）
        const previous = document.querySelector("dialog.drawer");
        const scrollTop = previous?.querySelector(".fd-body")?.scrollTop ?? 0;
        const before = document.activeElement;
        // 操作で決めたフォーカス先。無ければ、前のドロワーで値にあったフォーカスを同じ値へ戻す。初めて開くときは最初の値
        let focus = pendingFocus;
        pendingFocus = null;
        if (focus === null && previous !== null && before instanceof HTMLInputElement && previous.contains(before) && before.dataset["key"] !== undefined) {
            focus = { kind: "value", key: before.dataset["key"], value: before.value };
        }
        if (focus === null && previous === null)
            focus = { kind: "first" };
        const filtering = MindmapPreview.activeConditionCount(selected) > 0;
        const body = MindmapPreview.h({
            tag: "div",
            attrs: { class: "fd-body" },
            children: groups.map((group) => conditionGroup({ group, chosen: selected[group.key] ?? [], on })),
        });
        const drawer = MindmapPreview.h({
            tag: "dialog",
            attrs: {
                id: "drawer",
                class: narrow ? "drawer narrow" : "drawer",
                closedby: "none",
                "aria-labelledby": "drawer-title",
            },
            children: [
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "fd-top" },
                    children: [
                        MindmapPreview.h({ tag: "p", attrs: { class: "fd-title", id: "drawer-title" }, children: ["絞り込み"] }),
                        MindmapPreview.h({
                            tag: "span",
                            attrs: { class: "fd-count", "aria-live": "polite" },
                            children: [filtering ? `${total} 件中 ${shown} 件` : `${total} 件`],
                        }),
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "icon-btn", type: "button", "aria-label": "絞り込みを閉じる", onclick: on.close },
                            children: [MindmapPreview.icon("x")],
                        }),
                    ],
                }),
                body,
                MindmapPreview.h({
                    tag: "div",
                    attrs: { class: "fd-foot" },
                    children: [
                        filtering
                            ? MindmapPreview.h({
                                tag: "button",
                                attrs: {
                                    class: "btn ghost",
                                    type: "button",
                                    onclick: () => {
                                        pendingFocus = { kind: "first" };
                                        on.clearAll();
                                    },
                                },
                                children: ["すべて解除"],
                            })
                            : null,
                        MindmapPreview.h({ tag: "span", attrs: { class: "spacer" } }),
                        MindmapPreview.h({
                            tag: "button",
                            attrs: { class: "btn primary", type: "button", onclick: on.close },
                            children: [`${shown} 件を表示`],
                        }),
                    ],
                }),
            ],
        });
        // ドロワーの中の Esc で閉じる（ほかの Esc の処理には渡さない）
        drawer.addEventListener("keydown", (event) => {
            if (event.key !== "Escape")
                return;
            event.preventDefault();
            event.stopPropagation();
            on.close();
        });
        // 文書に入った後に、幕を付けずに開く（開くとフォーカスが動くので、移す先を決め直す）
        queueMicrotask(() => {
            if (!drawer.isConnected)
                return;
            if (!drawer.open)
                drawer.show();
            body.scrollTop = scrollTop;
            const target = focus === null ? null : focusTargetOf({ drawer, focus });
            if (target !== null) {
                target.focus();
            }
            else if (previous !== null && before instanceof HTMLElement && before.isConnected && !previous.contains(before)) {
                // 本文などにあったフォーカスは、開き直しで奪わない
                before.focus();
            }
        });
        return drawer;
    }
    MindmapPreview.filterDrawer = filterDrawer;
})(MindmapPreview || (MindmapPreview = {}));
