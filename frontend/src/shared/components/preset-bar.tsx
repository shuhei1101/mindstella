// 絞り込みのプリセットの並び。一覧の上に並び順で並べ、押すとそのプリセットで絞り込み、もう一度押すと解除する
import { Button } from "@/shared/components/ui/button";
import { cn } from "@/shared/lib/cn";

/** 並べるプリセット 1 件 */
export type PresetChoice = { name: string; description?: string; count: number };

/** プリセットを選んだ・解除したときに呼ぶ関数。解除は null */
export type SelectPreset = (name: string | null) => void;

export type PresetBarProps = {
  /** 並び順に並べたプリセット。空なら何も出さない */
  presets: PresetChoice[];
  /** 選んでいるプリセットの名前 */
  selected: string | null;
  onSelect: SelectPreset;
};

export const PresetBar = ({ presets, selected, onSelect }: PresetBarProps) => {
  if (presets.length === 0) return null;
  return (
    <div role="group" aria-label="絞り込みのプリセット" className="flex flex-wrap items-center gap-1">
      <span className="text-xs text-muted-foreground">プリセット</span>
      {presets.map((preset) => {
        const active = preset.name === selected;
        const empty = preset.count === 0;
        return (
          <Button
            key={preset.name}
            variant={active ? "default" : "outline"}
            aria-pressed={active}
            title={preset.description}
            className={cn(empty && !active && "border-dashed text-muted-foreground")}
            onClick={() => {
              onSelect(active ? null : preset.name);
            }}
          >
            {preset.name}
            <span className="font-mono text-xs" aria-label={`該当する項目 ${preset.count} 件`}>
              {empty ? "0 件" : preset.count}
            </span>
          </Button>
        );
      })}
    </div>
  );
};
