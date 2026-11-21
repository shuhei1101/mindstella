// Markdown の本文の差分のモック（#347）。描いた結果は mdmark の比較元の Markdown の色分け、原文の差分は mdmark の取り出し元の行の差分で描き、2 つを切り替える
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useEffect, useRef, useState } from "react";

import { getLibrary, useLibrary } from "@/shared/adapters/libraries";
import { MDMARK_FEATURES } from "@/shared/core/body-links";
import { cn } from "@/shared/lib/cn";

/** 本文の差分の見せ方 */
type View = "rendered" | "source";

/** 見せ方の切り替えのボタンの文言（HTML の本文の差分の切り替えと同じ文言） */
const VIEW_BUTTON = { rendered: "描いた結果", source: "原文の差分" } as const satisfies Record<View, string>;

/** 差分の取り出し元のリビジョン */
type Revision = { id: string; at: string; label?: string };

/** ここで使用する mdmark のインターフェース（比較元の Markdown と取り出し元） */
type MdmarkDiff = {
  mount: (
    root: HTMLElement,
    options: {
      markdown: string;
      config: { features: Record<string, boolean> };
      baseMarkdown?: string;
      docId?: string;
      diffMode?: "open";
      diffSource?: { revisions: (docId: string) => Promise<Revision[]>; content: (input: { docId: string; revisionId: string }) => Promise<string> };
    },
  ) => { destroy?: () => void } | undefined;
};

/** ストーリーの引数（選んだ時点の本文・今の本文・開いた時点の見せ方） */
type Args = { before: string; after: string; view: View };

/** 選んだ時点のリビジョンの ID と、今のリビジョンの ID */
const BEFORE_ID = "selected";
const AFTER_ID = "current";

/** 印刷もオンにした本文の機能 */
const FEATURES = { ...MDMARK_FEATURES, print: true };

/** 見せ方の切り替え */
const ViewSwitch = ({ view, onChange }: { view: View; onChange: (view: View) => void }) => (
  <div role="group" aria-label="本文の差分の見せ方" className="inline-flex rounded-control border border-border bg-card p-0.5">
    {(["rendered", "source"] as const).map((value) => (
      <button
        key={value}
        type="button"
        aria-pressed={view === value}
        onClick={() => {
          if (view !== value) onChange(value);
        }}
        className={cn("h-7 cursor-pointer rounded-control px-2 text-small hover:bg-accent", view === value && "bg-mark-weak font-medium hover:bg-mark-weak")}
      >
        {VIEW_BUTTON[value]}
      </button>
    ))}
  </div>
);

/** 切り替えと、選んだ見せ方で mdmark が描いた本文 */
const Host = ({ before, after, view: initial }: Args) => {
  const { status } = useLibrary("mdmark");
  const [view, setView] = useState<View>(initial);
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const root = host.current;
    if (root === null || status !== "ready") return undefined;
    const mdmark = getLibrary("mdmark") as MdmarkDiff;
    const target = document.createElement("div");
    target.className = "md";
    root.replaceChildren(target);
    // 取り出し元は、選んだ時点と今の 2 つだけを新しい順に返却する
    const diffSource = {
      revisions: () => Promise.resolve([
        { id: AFTER_ID, at: "2026-11-21T12:00:00+09:00", label: "今" },
        { id: BEFORE_ID, at: "2026-11-20T09:00:00+09:00", label: "選んだ時点" },
      ]),
      content: ({ revisionId }: { docId: string; revisionId: string }) => Promise.resolve(revisionId === BEFORE_ID ? before : after),
    };
    const handle =
      view === "rendered"
        ? mdmark.mount(target, { markdown: after, baseMarkdown: before, config: { features: FEATURES } })
        : mdmark.mount(target, { markdown: after, docId: "A-1", diffMode: "open", diffSource, config: { features: FEATURES } });
    return () => {
      handle?.destroy?.();
      root.replaceChildren();
    };
  }, [status, view, before, after]);
  return (
    <div className="flex max-w-3xl flex-col gap-3 p-4">
      <ViewSwitch view={view} onChange={setView} />
      <div ref={host} />
    </div>
  );
};

/** 選んだ時点の本文（段落 3 つと箇条書き） */
const BEFORE = [
  "# 保存先の決め方",
  "",
  "記録はワークスペースのフォルダに配置する。",
  "",
  "保存先は話し合いを始めるときに一度だけ決め、途中では変えない。",
  "",
  "保存した記録は、保持する回数を超えたものから削除する。",
  "",
  "- 記録の YAML",
  "- 本文の Markdown",
  "",
].join("\n");

/** 今の本文（1 つ目の段落の単語を書き換え、3 つ目の段落を削除し、箇条書きに 1 行追加した） */
const AFTER = [
  "# 保存先の決め方",
  "",
  "記録はワークスペースのフォルダにまとめて配置する。",
  "",
  "保存先は話し合いを始めるときに一度だけ決め、途中では変えない。",
  "",
  "- 記録の YAML",
  "- 本文の Markdown",
  "- 添付したファイル",
  "",
].join("\n");

const meta = {
  title: "Shared/MarkdownBodyDiff",
  component: Host,
  args: { before: BEFORE, after: AFTER, view: "rendered" },
} satisfies Meta<typeof Host>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 描いた結果。書き換えた段落と追加した行は追加の色、削除した段落は削除の色で、変更前の位置に出る。書き換えた段落の前の文と変わった単語は出さない */
export const Rendered: Story = {};

/** 原文の差分。選んだ時点と今の 2 つのリビジョンを mdmark の行の差分で並べ、書き換えた行の変わった単語だけを濃い色にする */
export const Source: Story = { args: { view: "source" } };

/** 描いた結果で、選んだ時点から変わっていない本文。色を付けずに今の本文だけを出す */
export const Unchanged: Story = { args: { before: AFTER } };
