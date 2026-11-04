import { Button } from "@/shared/components/ui/button";

type TopbarProps = {
  title: string;
  onSearch: () => void;
};

export const Topbar = ({ title, onSearch }: TopbarProps) => (
  <header className="flex items-center justify-between bg-background p-2 text-foreground">
    <h1 data-testid="topbar-title">{title}</h1>
    <Button onClick={onSearch}>検索</Button>
  </header>
);
