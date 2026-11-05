// Markdown で描く値
import { MarkdownBody } from "@/shared/components/markdown-body";
import { withHardBreaks } from "@/shared/core/body-links";

export const ValueText = ({ value }: { value: string | undefined }) => (value === undefined || value === "" ? null : <MarkdownBody source={withHardBreaks(value)} fold={false} />);
