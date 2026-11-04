import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import react, { reactCompilerPreset } from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const FRONTEND_DIR = fileURLToPath(new URL("./frontend", import.meta.url));
const OUT_DIR = fileURLToPath(new URL("./plugins/mindstella/skills/mindmap/preview/spa", import.meta.url));

export default defineConfig({
  root: FRONTEND_DIR,
  base: "/spa/",
  plugins: [react(), babel({ presets: [reactCompilerPreset()] }), tailwindcss()],
  resolve: { alias: { "@": `${FRONTEND_DIR}/src` } },
  build: { outDir: OUT_DIR, emptyOutDir: true },
});
