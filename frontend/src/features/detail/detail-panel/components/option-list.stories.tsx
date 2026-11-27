// 検討事項の案のカードのストーリー。利用者が案を選ぶ操作（選ぶ前・選んだ後・一言つき・決定済み）を描く
import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { fn } from "storybook/test";

import { OptionList, type OptionChoice } from "@/features/detail/detail-panel/components/option-list";
import type { Option } from "@/shared/core/records";

const OPTION_A: Option = { key: "A", content: "セルの番地で指す", pros: "書き方が短い", cons: "行を足すと参照が壊れる" };
const OPTION_B: Option = { key: "B", content: "列の名前で指す", pros: "行を足しても参照が壊れない", cons: "名前を付ける手間がかかる", recommended: true, reason: "参照は壊れず、計算式は読める名前で記載できるため" };
const OPTIONS: Option[] = [OPTION_A, OPTION_B];

/** 選ぶ・選び直す・取り消すを操作できる入れ物 */
const Interactive = ({ initial, options = OPTIONS }: { initial: OptionChoice | null; options?: Option[] }) => {
  const [choice, setChoice] = useState<OptionChoice | null>(initial);
  return (
    <div className="max-w-xl p-4">
      <OptionList options={options} previous={null} choice={choice} onChoose={setChoice} onCancelChoice={() => setChoice(null)} />
    </div>
  );
};

const meta = {
  title: "Features/Detail/OptionList",
  component: OptionList,
  args: { options: OPTIONS, previous: null, onChoose: fn(), onCancelChoice: fn() },
} satisfies Meta<typeof OptionList>;

export default meta;

type Story = StoryObj<typeof meta>;

/** 未決定で、まだ選んでいない。どの案のカードにも「この案を選ぶ」を出す */
export const NotChosen: Story = { render: () => <Interactive initial={null} /> };

/** 案 B を一言なしで選んだ。選んだカードを破線の枠と「選択済み（未送信）」の札にし、取り消すを出す */
export const Chosen: Story = { render: () => <Interactive initial={{ key: "B" }} /> };

/** 案 B を一言つきで選んだ */
export const ChosenWithNote: Story = { render: () => <Interactive initial={{ key: "B", note: "費用を優先する" }} /> };

/** 案 B を送信済み（記録の利用者の選択）。実線の枠線と「選択済み（送信済み）」の札にし、一言を編集・取り消すを出さない。ほかの案は選び直せる */
export const Sent: Story = { render: () => <Interactive initial={{ key: "B", note: "費用を優先する", sent: true }} /> };

/** 長い一言。カードの幅で折り返す */
export const LongText: Story = { render: () => <Interactive initial={{ key: "A", note: "行を足す運用はほとんど無く、書き方の短さを優先したい。参照が壊れたときは点検で見つけられるので、番地で指す方で進めてほしい" }} /> };

/** 案が多い */
export const Many: Story = {
  render: () => <Interactive initial={{ key: "C" }} options={[...OPTIONS, { key: "C", content: "名前付きの範囲で指す" }, { key: "D", content: "表ごとに ID の列を持たせて指す" }, { key: "E", content: "計算式を使わずに手で値を書く" }]} />,
};

/** 決定済み（AI が採用した）。選ぶ操作を出さない */
export const Decided: Story = {
  render: () => <Interactive initial={null} options={[{ ...OPTION_A, adopted: false }, { ...OPTION_B, adopted: true }]} />,
};

/** 幅 390px。ボタンの押せる領域を保ったまま折り返す */
export const Narrow: Story = {
  render: () => <Interactive initial={{ key: "B", note: "費用を優先する" }} />,
  parameters: { viewport: { options: { narrow: { name: "幅 390px", styles: { width: "390px", height: "844px" } } } } },
  globals: { viewport: { value: "narrow", isRotated: false } },
};
