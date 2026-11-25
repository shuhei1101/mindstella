// eslint.config.js の型（単体テストが設定を読み込む）
import type { Linter } from "eslint";

declare const config: Linter.Config[];
export default config;
