// 消した項目の帯のストーリー（部品設計『消した項目の帯.tsx』の状態）
import type { Meta, StoryObj } from "@storybook/react-vite";

import { RemovedBand } from "@/shared/components/removed-band";

const meta = {
  title: "Shared/RemovedBand",
  component: RemovedBand,
  args: { items: [] },
} satisfies Meta<typeof RemovedBand>;

export default meta;

type Story = StoryObj<typeof meta>;

export const One: Story = { args: {"items": [{"id": "N-6", "title": "ゴールを後から変える・足す・無しで始める"}]} };

export const ManyLongTitles: Story = { args: {"items": [{"id": "D-53", "title": "差分の印の色を、項目の種類ごとに変えるか"}, {"id": "D-54", "title": "変更履歴のモーダルを時系列の一覧にして、未読の印を付け、読んだ時点から後の書き換えだけを数えるか"}, {"id": "D-55", "title": "印の凡例を置くか"}]} };

export const Narrow: Story = { args: {"items": [{"id": "N-6", "title": "ゴールを後から変える・足す・無しで始める"}, {"id": "N-7", "title": "読み返したい点をメモする"}]} };
