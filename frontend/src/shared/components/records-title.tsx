import { useGetRecords } from "@/shared/api/generated/preview";

export const RecordsTitle = () => {
  const { data } = useGetRecords();
  return <p data-testid="records-title">{data?.data.settings.summary ?? "読み込み中"}</p>;
};
