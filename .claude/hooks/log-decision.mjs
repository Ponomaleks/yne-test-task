#!/usr/bin/env node
// Appends each AskUserQuestion call and its result to a git-ignored local log. Never blocks.
import { appendFileSync } from "node:fs";
import { join } from "node:path";

const dir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const file = join(dir, ".claude", "decisions-log.local.md");

const chunks = [];
process.stdin.on("data", (c) => chunks.push(c));
process.stdin.on("end", () => {
  let input = {};
  try {
    input = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
  } catch {}
  const stamp = new Date().toISOString();
  // First run: keep the raw payload (trimmed) so we can see the real field names.
  const raw = JSON.stringify(input).slice(0, 3000);
  appendFileSync(file, `\n## ${stamp}\n\`\`\`json\n${raw}\n\`\`\`\n`);
  process.exit(0);
});