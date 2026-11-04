import type { Meta, StoryObj } from "@storybook/react-vite";

import { RecordsTitle } from "@/shared/components/records-title";

const meta = { title: "Shared/RecordsTitle", component: RecordsTitle } satisfies Meta<typeof RecordsTitle>;

export default meta;

export const Default: StoryObj<typeof meta> = {};
