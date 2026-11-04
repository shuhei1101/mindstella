import type { Meta, StoryObj } from "@storybook/react-vite";

import { Topbar } from "@/shared/components/topbar";

const meta = { title: "Shared/Topbar", component: Topbar, args: { title: "話し合い", onSearch: () => undefined } } satisfies Meta<typeof Topbar>;

export default meta;

export const Default: StoryObj<typeof meta> = {};
