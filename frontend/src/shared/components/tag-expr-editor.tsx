// タグの式の編集。条件（含む・含まない）と束（すべて満たす・どれかを満たす・満たさない）を入れ子で組む
import { Icon } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Select } from "@/shared/components/ui/select";
import { MAX_TAG_EXPR_LAYERS, type PresetCondition, type PresetFilter } from "@/shared/core/presets";
import { cn } from "@/shared/lib/cn";

/** 選べるタグ 1 つ */
export type TagChoice = { value: string; count: number };

export type TagExprEditorProps = {
  expr: PresetFilter;
  tags: TagChoice[];
  onChange: (expr: PresetFilter) => void;
};

type BundleKind = "and" | "or" | "not";

const BUNDLE_LABEL = { and: "すべて満たす", or: "どれかを満たす", not: "満たさない" } as const satisfies Record<BundleKind, string>;

const BUNDLE_KINDS: readonly BundleKind[] = ["and", "or", "not"];

const emptyCondition = (): PresetCondition => ({ field: "tags", op: "eq", values: [] });

const kindOf = (node: PresetFilter): BundleKind | null => {
  if ("and" in node) return "and";
  if ("or" in node) return "or";
  if ("not" in node) return "not";
  return null;
};

const childrenOf = (node: PresetFilter): PresetFilter[] => {
  if ("and" in node) return node.and;
  if ("or" in node) return node.or;
  if ("not" in node) return [node.not];
  return [];
};

/** 束の種類と子から束を作る。`not` は先頭の子だけを持つ */
const bundleOf = (kind: BundleKind, children: PresetFilter[]): PresetFilter => {
  if (kind === "not") return { not: children[0] ?? emptyCondition() };
  return kind === "and" ? { and: children } : { or: children };
};

type RowProps = { tags: TagChoice[]; onRemove: (() => void) | null };

const ConditionRow = ({ node, tags, onChange, onRemove }: RowProps & { node: PresetCondition; onChange: (node: PresetCondition) => void }) => (
  <div className="flex flex-col gap-1 rounded-control border border-border-soft p-1.5">
    <div className="flex items-center gap-1">
      <Select
        aria-label="タグの比べ方"
        className="w-auto"
        value={node.op}
        onChange={(event) => {
          onChange({ ...node, op: event.target.value === "ne" ? "ne" : "eq" });
        }}
      >
        <option value="eq">含む</option>
        <option value="ne">含まない</option>
      </Select>
      {node.op === "eq" && node.values.length > 1 ? (
        <Select
          aria-label="選んだタグの組み合わせ方"
          className="w-auto"
          value={node.match ?? "any"}
          onChange={(event) => {
            onChange(event.target.value === "all" ? { ...node, match: "all" } : { field: node.field, op: node.op, values: node.values });
          }}
        >
          <option value="all">すべて</option>
          <option value="any">どれか</option>
        </Select>
      ) : null}
      {onRemove === null ? null : (
        <Button variant="ghost" size="icon" aria-label="条件を削除" className="ml-auto" onClick={onRemove}>
          <Icon name="x" />
        </Button>
      )}
    </div>
    <ul className="flex flex-wrap gap-1" aria-label="タグ">
      {tags.map((tag) => {
        const chosen = node.values.includes(tag.value);
        return (
          <li key={tag.value}>
            <button
              type="button"
              aria-pressed={chosen}
              className={cn(
                "flex h-7 items-center gap-1 rounded-full border border-border bg-card px-2 text-xs hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring",
                chosen && "border-mark-line bg-mark-weak font-medium hover:bg-mark-weak",
                tag.count === 0 && !chosen && "text-muted-foreground",
              )}
              onClick={() => {
                onChange({ ...node, values: chosen ? node.values.filter((value) => value !== tag.value) : [...node.values, tag.value] });
              }}
            >
              {tag.value}
              <span className="font-mono text-muted-foreground">{tag.count}</span>
            </button>
          </li>
        );
      })}
    </ul>
  </div>
);

const Node = ({ node, tags, layer, onChange, onRemove }: RowProps & { node: PresetFilter; layer: number; onChange: (node: PresetFilter) => void }) => {
  const kind = kindOf(node);
  if (kind === null) return <ConditionRow node={node as PresetCondition} tags={tags} onChange={onChange} onRemove={onRemove} />;
  const children = childrenOf(node);
  const replaceChild = (index: number, next: PresetFilter): void => {
    onChange(bundleOf(kind, children.map((child, at) => (at === index ? next : child))));
  };
  const removeChild = (index: number): void => {
    onChange(bundleOf(kind, children.filter((_, at) => at !== index)));
  };
  return (
    <div className={cn("flex flex-col gap-1.5", layer > 1 && "rounded-control border border-border p-1.5")}>
      <div className="flex items-center gap-1">
        <Select
          aria-label="条件の組み合わせ方"
          className="w-auto"
          value={kind}
          onChange={(event) => {
            const next = BUNDLE_KINDS.find((value) => value === event.target.value) ?? kind;
            onChange(bundleOf(next, children));
          }}
        >
          {BUNDLE_KINDS.map((value) => (
            <option key={value} value={value}>
              {BUNDLE_LABEL[value]}
            </option>
          ))}
        </Select>
        {onRemove === null ? null : (
          <Button variant="ghost" size="icon" aria-label="グループを削除" className="ml-auto" onClick={onRemove}>
            <Icon name="x" />
          </Button>
        )}
      </div>
      <div className="flex flex-col gap-1.5 border-l-2 border-border-soft pl-2">
        {children.map((child, index) => (
          <Node
            // 式の子は ID を持たず、並び順で区別する
            key={index}
            node={child}
            tags={tags}
            layer={layer + 1}
            onChange={(next) => { replaceChild(index, next); }}
            onRemove={children.length > 1 ? () => { removeChild(index); } : null}
          />
        ))}
      </div>
      {kind === "not" ? null : (
        <div className="flex flex-wrap gap-1">
          <Button variant="outline" onClick={() => { onChange(bundleOf(kind, [...children, emptyCondition()])); }}>
            <Icon name="plus" />
            条件追加
          </Button>
          {layer < MAX_TAG_EXPR_LAYERS ? (
            <Button variant="outline" onClick={() => { onChange(bundleOf(kind, [...children, { and: [emptyCondition()] }])); }}>
              <Icon name="plus" />
              グループ追加
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
};

export const TagExprEditor = ({ expr, tags, onChange }: TagExprEditorProps) => {
  // 最上位は常に束にして、条件の追加と組み合わせ方の切り替えを出す
  const root: PresetFilter = kindOf(expr) === null ? { and: [expr] } : expr;
  return <Node node={root} tags={tags} layer={1} onChange={onChange} onRemove={null} />;
};
