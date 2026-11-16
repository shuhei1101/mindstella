import { writeFileSync } from "node:fs";
const m = await import("./mdmark/tests/unit/helpers/retired-document.ts");
writeFileSync("ws/docs/Z-retired.md", m.RETIRED_DOCUMENT);
writeFileSync("expected-retired.md", m.RETIRED_DOCUMENT_CONVERTED);
console.log(Object.keys(m));
