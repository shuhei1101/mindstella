// 本文の印のツールチップのストーリー（部品設計『本文の印のツールチップ.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { fn } from "storybook/test";

import { TermTip } from "@/shared/components/term-tip";
import type { Item } from "@/shared/core/records";
import type { TermTipEntry } from "@/shared/core/term-tips";

const term = (id: string, title: string, meaning: string): TermTipEntry => ({ kind: "terms", item: { id, title, meaning } as Item });
const doc = (id: string, title: string, description?: string): TermTipEntry => ({ kind: "docs", item: { id, title, ...(description === undefined ? {} : { description }) } as Item });
const research = (id: string, title: string): TermTipEntry => ({ kind: "research", item: { id, title, description: "調査の説明" } as Item });

/** 印を置いて、その印を起点にツールチップを出す */
const Host = ({ entries, placement }: { entries: TermTipEntry[]; placement: "above" | "top" | "fill" }) => {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  const on = { open: fn(), close: fn() };
  const top = placement === "above" ? "60vh" : placement === "top" ? "4px" : "50vh";
  return (
    <div>
      <a ref={setAnchor} href="#mark" style={{ position: "fixed", left: 16, top }}>
        本文の印
      </a>
      {anchor === null ? null : <TermTip entries={entries} anchor={anchor} on={on} />}
    </div>
  );
};

const meta = {
  title: "Shared/TermTip",
  component: Host,
  args: { entries: [term("G-1", "移し替え", "版を上げる作業")], placement: "above" },
} satisfies Meta<typeof Host>;

export default meta;

type Story = StoryObj<typeof meta>;

const manyDocs = ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6"].map((id) => doc(id, `${id} の資料`, "資料の説明"));

export const TermOnly: Story = {};
export const Few: Story = { args: { entries: [term("G-1", "移し替え", "版を上げる作業"), doc("A-1", "資料", "資料の説明"), research("R-1", "調査")] } };
export const DocOnly: Story = { args: { entries: [doc("A-1", "資料", "資料の説明")] } };
export const NoDescription: Story = { args: { entries: [doc("A-1", "説明の無い資料")] } };
export const Many: Story = { args: { entries: [term("G-1", "移し替え", "版を上げる作業"), ...manyDocs, research("R-1", "調査")] } };
export const Below: Story = { args: { placement: "top" } };
export const Shrunk: Story = { args: { placement: "fill", entries: [term("G-1", "移し替え", "版を上げる作業"), ...manyDocs, ...manyDocs, research("R-1", "調査")] } };
export const LinkFocus: Story = { args: { entries: [doc("A-1", "資料", "資料の説明")] } };
export const LongNarrow: Story = { args: { entries: [doc("A-1", "とても長いタイトルの資料を幅の狭い画面で出したときに折り返して画面の端の内側に収まることを確かめる", "長い説明の文が続いても折り返す")] } };
export const SeveralTerms: Story = { args: { entries: [term("G-1", "移し替え", "版を上げる作業"), term("G-2", "移行", "別の意味")] } };
