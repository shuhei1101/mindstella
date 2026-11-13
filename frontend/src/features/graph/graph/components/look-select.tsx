// ネットワークの見た目のドロップダウン。既定の見た目に「（既定）」を添える
import { Select } from "@/shared/components/ui/select";
import { lookLabel } from "@/shared/core/display";
import type { NetworkLook } from "@/shared/core/records";

/** 選択肢の並び */
const NETWORK_LOOKS: readonly NetworkLook[] = ["glow", "starlight", "constellation", "deep", "dust"];

export type LookSelectProps = { value: NetworkLook; defaultLook: NetworkLook; onChange: (look: NetworkLook) => void };

export const LookSelect = ({ value, defaultLook, onChange }: LookSelectProps) => (
  <Select
    aria-label="ネットワークの見た目"
    className="w-auto bg-card"
    value={value}
    onChange={(event) => {
      onChange(event.target.value as NetworkLook);
    }}
  >
    {NETWORK_LOOKS.map((look) => (
      <option key={look} value={look}>
        {look === defaultLook ? `${lookLabel(look)}（既定）` : lookLabel(look)}
      </option>
    ))}
  </Select>
);
