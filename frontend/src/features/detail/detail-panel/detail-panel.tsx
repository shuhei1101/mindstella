// 詳細パネル（画面設計『詳細パネル.tsx』）。項目 1 件の中身を本文の右に出し、差分の表示の間は前後の差分を出す
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { DetailEditor, type EditChange } from "@/features/detail/detail-panel/components/detail-editor";
import { DetailHeader } from "@/features/detail/detail-panel/components/detail-header";
import { DetailResizer, PANEL_WIDTH } from "@/features/detail/detail-panel/components/detail-resizer";
import { BodyView, type BodyLayout } from "@/features/detail/detail-panel/components/body-view";
import { DetailComments } from "@/features/detail/detail-panel/components/detail-comments";
import { DiffDeadlineContext, KeyDiff, keyDiffs, nextDiffDeadline, valueText, type KeyDiffs } from "@/features/detail/detail-panel/components/key-diff";
import { OptionList } from "@/features/detail/detail-panel/components/option-list";
import { RelatedList } from "@/features/detail/detail-panel/components/related-list";
import { ValueText } from "@/features/detail/detail-panel/components/value-text";
import { DiagramViewer, type DiagramViewerProps } from "@/features/detail/diagram-viewer/diagram-viewer";
import { DiffMark } from "@/shared/components/diff-mark";
import { DiffMinimap } from "@/shared/components/diff-minimap";
import { Icon, StatusMark } from "@/shared/components/icon";
import { TagList } from "@/shared/components/tag-list";
import { WithdrawnBadge } from "@/shared/components/withdrawn-badge";
import { LINE_ATTR, VALUE_KEY_ATTR } from "@/shared/core/body-links";
import { HTML_BODY_ATTR } from "@/shared/core/body-render";
import { buildVersions, type DiffPoint, type VersionPair } from "@/shared/core/diff";
import { pendingMarkOf, type BlockedEdit, type PendingMarkKind } from "@/shared/core/edits";
import type { BodyView as BodyDisplay } from "@/shared/core/markdown-decorate";
import { relatedItems, tagNames, type Item, type Kind, type RecordIndex, type Tag } from "@/shared/core/records";
import { applyHighlight } from "@/shared/core/term-tips";
import { useDiffView } from "@/shared/hooks/use-diff-view";
import { useAddEdit, useCancelEdit } from "@/shared/hooks/use-edits";
import { usePreviewSearch } from "@/shared/hooks/use-preview-search";
import { useRecords } from "@/shared/hooks/use-records";
import { useEditSessionStore } from "@/shared/stores/edit-session-store";
import { useLocationHighlight } from "@/shared/stores/location-highlight-store";
import { readBodyScrolls, readPrefs, usePrefs, writeBodyScroll, writePrefs } from "@/shared/stores/prefs-store";

const NOTE_TRIMMED = "このまとまりの前後を組み立てられません。保持する回数を超えた古い変更履歴は消えています。今の内容を出しています。";

/** 差分の表示で開いた項目の内容 */
type DetailDiff = { point: DiffPoint; kind: "new" | "changed"; versions: VersionPair | null; keys: KeyDiffs | null; shown: Item; body: string | undefined };

const resolveDiff = (id: string, index: RecordIndex, diff: DiffPoint | null): DetailDiff | null => {
  const entry = index.byId.get(id);
  if (diff === null || entry === undefined) return null;
  const { item } = entry;
  const body = index.data.bodies[item.body ?? ""];
  if (diff.added.has(id)) return { point: diff, kind: "new", versions: null, keys: null, shown: item, body };
  if (!diff.changed.has(id)) return null;
  const versions = buildVersions(item, body ?? "", diff);
  if (versions.before === null || versions.trimmed) return { point: diff, kind: "changed", versions, keys: null, shown: item, body };
  return { point: diff, kind: "changed", versions, keys: keyDiffs(versions.before, versions.after), shown: versions.after, body: versions.afterBody ?? body };
};

const Section = ({ label, children }: { label: string; children: ReactNode }) => (
  <section className="flex flex-col gap-1">
    <h3 className="m-0 text-h2 font-semibold">{label}</h3>
    {children}
  </section>
);

const Status = ({ value }: { value: unknown }) =>
  typeof value === "string" ? (
    <span className="inline-flex items-center gap-1 text-small">
      <StatusMark status={value} />
      {value}
    </span>
  ) : null;

/** キーの値。変わっていれば前の値と今の値を並べる */
const KeyValue = ({ name, value, keys, top }: { name: string; value: string | undefined; keys: KeyDiffs | null; top?: boolean }) =>
  keys?.has(name) === true ? <KeyDiff was={valueText(keys.left[name])} now={valueText(keys.right[name])} /> : top === true ? <ValueText value={value} /> : <>{value}</>;

const Labelled = ({ label, name, value, keys }: { label: string; name: string; value: string | undefined; keys: KeyDiffs | null }) => {
  if ((value === undefined || value === "") && keys?.has(name) !== true) return null;
  return (
    <div data-key={name} className="rounded-control bg-muted p-2">
      <b className="text-xs text-muted-foreground">{label}</b>
      <KeyValue name={name} value={value} keys={keys} top />
    </div>
  );
};

const Meta = ({ item, index, keys }: { item: Item; index: RecordIndex; keys: KeyDiffs | null }) => {
  const rows: [string, string, string | undefined][] = [
    [index.data.settings.target_label, "target", item.target],
    ["カテゴリー", "category", item.category],
    ["フェーズ", "phase", item.phase],
    ["影響度", "weight", item.weight],
    ["種類", "kind", item.kind],
    ["確度", "confidence", item.confidence],
    ["日付", "date", item.date],
    ["更新日", "updated", item.updated],
  ];
  const tagsChanged = keys?.has("tags") === true;
  return (
    <dl className="grid grid-cols-meta gap-x-2 text-small">
      {rows
        .filter(([, name, value]) => (value !== undefined && value !== "") || keys?.has(name) === true)
        .map(([label, name, value]) => (
          <div key={name} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd>
              <KeyValue name={name} value={value} keys={keys} />
            </dd>
          </div>
        ))}
      {(item.tags ?? []).length > 0 || tagsChanged ? (
        <div className="contents">
          <dt className="text-muted-foreground">タグ</dt>
          <dd className="flex flex-wrap gap-1">{tagsChanged ? <KeyDiff was={tagNames(keys?.left["tags"] as Tag[] | undefined).join("、")} now={tagNames(keys?.right["tags"] as Tag[] | undefined).join("、")} /> : <TagList values={item.tags} />}</dd>
        </div>
      ) : null}
    </dl>
  );
};

/** 本文の差分の並べ方・本文の見せ方（端末の上書き） */
const bodyDisplayOf = (): BodyDisplay => {
  const prefs = readPrefs();
  return { pin: prefs.tablePin !== false, head: prefs.tableHead !== false, stripes: prefs.tableStripes === true, fold: prefs.sectionFold !== false };
};

export type DetailContentProps = { id: string; index: RecordIndex; full: boolean; onClose: () => void; onTitle?: (id: string) => string };

/** 見出しと本文。パネルと全画面が共通で使う */
// eslint-disable-next-line sonarjs/cognitive-complexity -- 今の画面と同じ分岐を 1 か所で読めるように保つ
export const DetailContent = ({ id, index, full }: Omit<DetailContentProps, "onClose" | "onTitle">) => {
  const { search, openItem, closeItem, setFull, setHeading, setDiff } = usePreviewSearch();
  const { point } = useDiffView();
  const { edits } = useRecords();
  const add = useAddEdit();
  const cancel = useCancelEdit();
  const [editing, setEditing] = useState(false);
  const [layout, setLayout] = useState<BodyLayout>(() => (readPrefs().bodyLayout === "side" ? "side" : "inline"));
  const [diagram, setDiagram] = useState<Omit<DiagramViewerProps, "onClose"> | null>(null);
  const blockedEdits = useEditSessionStore((state) => state.blocked);
  // 語の差分の打ち切りの時刻は、描き直す項目と時点ごとに 1 つ
  // eslint-disable-next-line react-hooks/exhaustive-deps -- 項目と時点が変わるたびに決め直す
  const deadline = useMemo(() => nextDiffDeadline(), [id, point?.sel]);
  const [display] = useState(bodyDisplayOf);
  const prefs = usePrefs();
  // 本文の先頭のタイトルが、本文のスクロール領域の上へ外れているか
  const [titleElement, setTitleElement] = useState<HTMLElement | null>(null);
  const [titleOut, setTitleOut] = useState(false);
  useEffect(() => {
    const scroller = titleElement?.closest(".panel-body") ?? null;
    if (titleElement === null || scroller === null) return undefined;
    const update = (): void => {
      setTitleOut(titleElement.getBoundingClientRect().bottom <= scroller.getBoundingClientRect().top);
    };
    scroller.addEventListener("scroll", update, { passive: true });
    return () => { scroller.removeEventListener("scroll", update); };
  }, [titleElement]);
  // コメントの一覧から開いたとき、描いた本文の中の書き込みの箇所を示す（描き終えるのを本文の要素の変化で待つ）
  const loc = useLocationHighlight(id);
  useEffect(() => {
    const root = titleElement?.closest(".panel-body") ?? null;
    if (loc === null || root === null) return undefined;
    const ready = loc.kind === "value" ? `[${VALUE_KEY_ATTR}]` : `.md [${LINE_ATTR}], iframe[${HTML_BODY_ATTR}]`;
    const observer = new MutationObserver(() => { apply(); });
    const apply = (): void => {
      if (root.querySelector(ready) === null) return;
      observer.disconnect();
      applyHighlight({ root, loc });
    };
    observer.observe(root, { childList: true, subtree: true });
    apply();
    return () => {
      observer.disconnect();
      for (const element of root.querySelectorAll(".loc-hit")) element.classList.remove("loc-hit");
    };
  }, [titleElement, loc]);
  const entry = index.byId.get(id);
  if (entry === undefined) return null;
  const { kind } = entry;
  const diff = resolveDiff(id, index, point);
  const item = diff?.shown ?? entry.item;
  const keys = diff?.keys ?? null;
  const related = relatedItems({ id, index });
  const source = diff?.body ?? index.data.bodies[item.body ?? ""];
  const body = (label: string) =>
    source === undefined ? null : (
      <BodyView label={label} item={entry.item} id={id} index={index} source={source} versions={diff?.versions ?? null} layout={layout} display={display} heading={search.h} deadline={deadline} onOpen={openItem} onHeading={setHeading} onChangeSet={setDiff} onLayout={(next) => { setLayout(next); writePrefs({ bodyLayout: next === "side" ? "side" : null }); }} onDiagram={({ svg, ...figure }) => { setDiagram({ ...figure, svg: svg.outerHTML }); }} />
    );
  const relation = (label: string, ids: readonly string[]) => <RelatedList label={label} ids={ids} index={index} onOpen={openItem} />;
  const list = (label: string, name: string, values: readonly string[] | undefined) =>
    keys?.has(name) === true ? <Section label={label}><KeyDiff was={valueText(keys.left[name])} now={valueText(keys.right[name])} /></Section> : (values ?? []).length > 0 ? <Section label={label}><div className="flex flex-wrap gap-1"><TagList values={values} /></div></Section> : null;
  const previous = keys?.has("options") === true ? (keys.left["options"] as Item["options"]) ?? [] : null;
  const description = <Labelled label="説明" name="description" value={item.description} keys={keys} />;
  const byKind: Record<Kind, ReactNode> = {
    decisions: (
      <>
        <KeyLead name="lead" value={item.lead} keys={keys} />
        {(item.options ?? []).length > 0 || previous !== null ? <Section label="案"><OptionList options={item.options ?? []} previous={previous} /></Section> : null}
        {item.answer !== undefined || item.reason !== undefined || keys?.has("answer") === true || keys?.has("reason") === true ? (
          <Section label="採用した案と理由">
            <Labelled label="決定内容" name="answer" value={item.answer} keys={keys} />
            <Labelled label="理由" name="reason" value={item.reason} keys={keys} />
          </Section>
        ) : null}
        {body("本文")}
        {relation("前提", related.prerequisites)}
        {relation("後続の項目", related.successors)}
        {relation("関連タスク", related.tasks)}
        {relation("経緯（会話ログ）", related.logs)}
      </>
    ),
    tasks: (
      <>
        <Labelled label="理由" name="reason" value={item.reason} keys={keys} />
        {relation("進める検討事項", item.for ?? [])}
        {relation("前提", related.prerequisites)}
        {relation("結果", item.result === undefined ? [] : [item.result])}
        {body("本文")}
      </>
    ),
    research: (
      <>
        <KeyLead name="question" value={item.question} keys={keys} />
        {description}
        <Labelled label="結論" name="conclusion" value={item.conclusion} keys={keys} />
        {list("エイリアス", "aliases", item.aliases)}
        {list("調査の観点", "angles", item.angles)}
        {body("本文")}
      </>
    ),
    docs: (
      <>
        {description}
        {list("エイリアス", "aliases", item.aliases)}
        {body("本文")}
      </>
    ),
    terms: (
      <>
        <Labelled label="意味" name="meaning" value={item.meaning} keys={keys} />
        {list("別名", "aliases", item.aliases)}
        {list("使わない表記", "avoid", item.avoid)}
        {body("本文")}
      </>
    ),
    notes: (
      <>
        <KeyLead name="content" value={item.content} keys={keys} />
        {body("本文")}
      </>
    ),
    logs: body("要約"),
  };
  const canEdit = point === null;
  const marks: Record<string, PendingMarkKind> = {};
  const blockedIds = new Set(blockedEdits.map((entry) => entry.id));
  const blockedByKey: Record<string, BlockedEdit> = {};
  for (const edit of edits.filter((candidate) => candidate.target === id)) {
    const name = edit.op === "adopt" ? String(edit.value) : edit.key;
    if (name === null) continue;
    marks[name] = pendingMarkOf({ edits, blocked: blockedIds, target: id, key: name }) ?? "pending";
    const entry = blockedEdits.find((candidate) => candidate.id === edit.id);
    if (entry !== undefined) blockedByKey[name] = entry;
  }
  const removal = edits.find((edit) => edit.target === id && edit.op === "item-remove");
  const referrers = [...index.byId.values()].filter(({ item: other }) => (other.depends_on ?? []).includes(id) || (other.related ?? []).includes(id)).map(({ item: other }) => other.id);
  const change = ({ op, key, value }: EditChange): void => { add.mutate({ op, target: id, key, value }); };
  return (
    <DiffDeadlineContext.Provider value={deadline}>
      <DetailHeader item={entry.item} kind={kind} index={index} full={full} editable={canEdit} editing={editing} pending={pendingMarkOf({ edits, blocked: blockedIds, target: id })} showTitle={titleElement !== null && titleOut} onToggleEdit={() => { setEditing(!editing); }} onToggleFull={() => { setFull(!full); }} onClose={closeItem} />
      <DiffMinimap shown={diff !== null && prefs.minimap !== false} initialScrollTop={search.h === undefined ? readBodyScrolls()[id] : undefined} onBodyScroll={(top) => { writeBodyScroll(id, top); }}>
        {editing ? (
          <DetailEditor kind={kind} item={entry.item} settings={index.data.settings} marks={marks} blocked={blockedByKey} removing={removal !== undefined} removedOptions={edits.filter((edit) => edit.target === id && edit.op === "option-remove").map((edit) => edit.key ?? "")} referrers={referrers} usedTags={[...new Set([...index.byId.values()].flatMap(({ item: other }) => tagNames(other.tags)))]} body={index.data.bodies[entry.item.body ?? ""]} onChange={change} onRemove={() => { add.mutate({ op: "item-remove", target: id }); }} onCancelRemove={() => { if (removal !== undefined) cancel.mutate(removal.id); }} />
        ) : (
          <div className="flex flex-col gap-3 p-3">
            {diff === null ? null : (
              <div className="flex items-center gap-2 text-small">
                <span className="inline-flex items-center gap-1 font-medium">
                  <Icon name="history" className="size-4" />
                  {diff.point.name}
                </span>
                <span className="text-muted-foreground">{diff.point.sub}</span>
              </div>
            )}
            {diff?.versions?.trimmed === true ? <p role="note" className="text-small text-muted-foreground">{NOTE_TRIMMED}</p> : null}
            <div data-key="status">{keys?.has("status") === true ? <KeyDiff was={<Status value={keys.left["status"]} />} now={<Status value={keys.right["status"]} />} plain /> : <Status value={item.status} />}</div>
            <h2 ref={setTitleElement} data-key="title" className="m-0 flex flex-wrap items-center gap-1 text-next font-semibold">
              <KeyValue name="title" value={item.title} keys={keys} />
              {diff?.kind === "new" ? <DiffMark kind="new" labeled /> : null}
              {item.withdrawn === true ? <WithdrawnBadge large /> : null}
            </h2>
            <Meta item={item} index={index} keys={keys} />
            {kind === "decisions" || kind === "tasks" ? null : <Labelled label="取り下げた理由" name="reason" value={item.reason} keys={keys} />}
            {byKind[kind]}
            {(item.links ?? []).length > 0 ? (
              <Section label="リンク">
                <ul className="flex flex-col gap-1">
                  {(item.links ?? []).map((link) => (
                    <li key={link.url} className="flex items-center gap-1 text-small">
                      <Icon name="link" className="size-3" />
                      <a href={link.url} target="_blank" rel="noopener noreferrer" className="text-mark underline">
                        {link.title}
                      </a>
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}
            {relation(kind === "logs" ? "更新した項目" : "関連", related.related)}
            {relation("参照元", related.referencedBy)}
            <DetailComments id={id} titles={(target) => index.byId.get(target)?.item.title ?? null} changeSets={(set) => index.data.changes.sets.find((one) => one.id === set)?.summary ?? null} onOpenItem={openItem} onOpenChangeSet={setDiff} />
          </div>
        )}
      </DiffMinimap>
      {diagram === null ? null : <DiagramViewer {...diagram} onClose={() => { setDiagram(null); }} />}
    </DiffDeadlineContext.Provider>
  );
};

const KeyLead = ({ name, value, keys }: { name: string; value: string | undefined; keys: KeyDiffs | null }) => {
  if ((value === undefined || value === "") && keys?.has(name) !== true) return null;
  return (
    <div data-key={name}>
      <KeyValue name={name} value={value} keys={keys} top />
    </div>
  );
};

/** そのタブで変えた幅を残す sessionStorage のキー（今の画面と同じ） */
const PANEL_WIDTH_KEY = "mindmap-panel-width";

const readPanelWidth = (): number => {
  const saved = sessionStorage.getItem(PANEL_WIDTH_KEY);
  return saved !== null && /^[1-9]\d*$/.test(saved) ? Number(saved) : PANEL_WIDTH.default;
};

export type DetailPanelProps = { id: string; index: RecordIndex };

export const DetailPanel = ({ id, index }: DetailPanelProps) => {
  const [width, setWidth] = useState(readPanelWidth);
  return (
    <aside aria-label="詳細" style={{ width }} className="relative flex min-h-0 flex-none flex-col border-l border-border bg-card max-lg:fixed max-lg:inset-0 max-lg:z-30 max-lg:w-full!">
      <DetailResizer
        width={width}
        onChange={(next) => {
          setWidth(next);
          sessionStorage.setItem(PANEL_WIDTH_KEY, String(next));
        }}
      />
      <DetailContent key={id} id={id} index={index} full={false} />
    </aside>
  );
};
