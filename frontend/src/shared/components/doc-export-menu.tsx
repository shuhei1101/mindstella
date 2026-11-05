// 資料のエクスポートのメニュー（部品設計『資料のエクスポートのメニュー.tsx』）。形式の選択・Markdown の警告・処理中・エラーを中身を替えて出す
import { useRef, useState } from "react";

import { Icon, type IconName } from "@/shared/components/icon";
import { Button } from "@/shared/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/components/ui/popover";
import { buildDocHtml, downloadText, mdmarkAssets, stripEmbeddedHtml } from "@/shared/core/doc-export";
import type { Item, RecordIndex } from "@/shared/core/records";

type View = "choose" | "warn" | "busy" | "error";

const TITLES: Record<View, string> = { choose: "エクスポート", busy: "エクスポート", warn: "Markdown でエクスポートしますか?", error: "エクスポートできませんでした" };

const Row = ({ icon, name, sub, busy, disabled, focused, onPress }: { icon: IconName; name: string; sub: string; busy: boolean; disabled: boolean; focused: boolean; onPress: () => void }) => (
  // eslint-disable-next-line jsx-a11y/no-autofocus -- 中身を替えたときに選んでいた行へフォーカスを戻す
  <button type="button" autoFocus={focused} aria-disabled={disabled || undefined} className="flex w-72 cursor-pointer items-start gap-2 rounded-control p-2 text-left hover:bg-accent" onClick={() => { if (!disabled) onPress(); }}>
    <Icon name={icon} />
    <span className="flex flex-col">
      <span className="text-small font-medium">{name}</span>
      <span role={busy ? "status" : undefined} className="text-xs text-muted-foreground">
        {sub}
      </span>
    </span>
  </button>
);

/** メニューの中身 */
export type DocExportView = View;

export type DocExportMenuProps = {
  view?: DocExportView;
  /** 中身を出した時点でフォーカスを置く行 */
  focus?: "html" | "md";
  onFormat: (format: "html" | "md") => void;
  onConfirm: () => void;
  onBack: () => void;
  onRetry: () => void;
};

/** メニューの中身。開閉とエクスポートの処理は `DocExportControl` が持つ */
export const DocExportMenu = ({ view = "choose", focus = "html", onFormat, onConfirm, onBack, onRetry }: DocExportMenuProps) => {
  const busy = view === "busy";
  return (
    <div role="dialog" aria-label={TITLES[view]} aria-busy={busy || undefined}>
      <p className="mb-1 text-small font-medium">{TITLES[view]}</p>
      {view === "choose" || busy ? (
        <div role="group" aria-label="エクスポート">
          <Row icon="code" name="HTML でエクスポート" sub={busy ? "エクスポートしています…" : "スタイルと用語のツールチップを含む 1 つのファイル"} busy={busy} disabled={busy} focused={busy || focus === "html"} onPress={() => { onFormat("html"); }} />
          <Row icon="doc" name="Markdown でエクスポート" sub="本文の Markdown だけ" busy={false} disabled={busy} focused={!busy && focus === "md"} onPress={() => { onFormat("md"); }} />
        </div>
      ) : (
        <div className="flex w-72 flex-col gap-2">
          <p role={view === "error" ? "alert" : undefined} className="flex gap-1 text-small">
            <Icon name="alert" />
            {view === "warn" ? "埋め込んだ HTML・チャート・操作できる部品は含まれず、共通のスタイルも外れます。" : "mdmark のスタイルとスクリプトを読み込めませんでした。ネットワークにつながっているか確かめて、再試行してください。"}
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onBack}>
              戻る
            </Button>
            {/* eslint-disable-next-line jsx-a11y/no-autofocus -- 中身を替えたときに主のボタンへフォーカスを移す */}
            <Button autoFocus onClick={view === "warn" ? onConfirm : onRetry}>
              {view === "warn" ? "エクスポート" : "再試行"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export type DocExportControlProps = { item: Item; source: string; index: RecordIndex };

/** 詳細の見出しの「エクスポート」。メニューの開閉とエクスポートの処理を持つ */
export const DocExportControl = ({ item, source, index }: DocExportControlProps) => {
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>("choose");
  const [focus, setFocus] = useState<"html" | "md">("html");
  // 組み立てている間に閉じたとき、組み立て終えたファイルを保存させない
  const generation = useRef(0);
  const exportHtml = async (): Promise<void> => {
    setView("busy");
    generation.current += 1;
    const mine = generation.current;
    const assets = await mdmarkAssets();
    if (mine !== generation.current) return;
    if (!assets.ok) {
      setView("error");
      return;
    }
    try {
      downloadText({ name: `${item.id}.html`, text: buildDocHtml({ item, source, index, assets }), type: "text/html" });
      setOpen(false);
    } catch {
      setView("error");
    }
  };
  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) {
          setView("choose");
          setFocus("html");
        } else {
          generation.current += 1;
        }
      }}
    >
      <PopoverTrigger render={<Button variant="ghost" size="icon" aria-label="エクスポート" title="エクスポート" />}>
        <Icon name="download" />
      </PopoverTrigger>
      <PopoverContent>
        <DocExportMenu
          view={view}
          focus={focus}
          onFormat={(format) => {
            if (format === "html") void exportHtml();
            else setView("warn");
          }}
          onConfirm={() => {
            downloadText({ name: `${item.id}.md`, text: stripEmbeddedHtml(source), type: "text/markdown" });
            setOpen(false);
          }}
          onBack={() => {
            setFocus(view === "warn" ? "md" : "html");
            setView("choose");
          }}
          onRetry={() => { void exportHtml(); }}
        />
      </PopoverContent>
    </Popover>
  );
};
