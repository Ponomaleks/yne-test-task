#!/usr/bin/env node
// PreToolUse guard: blocks Claude from reading or leaking secret files,
// including via shell commands (permission deny rules do not cover `cat .env`).
// Exit code 2 = block the tool call; stderr is shown to Claude as the reason.
// Fail-closed: any error, empty payload, or unparseable payload is blocked.

const SECRET_PATH = /(^|[\/\s"'=<(:])(\.env(?!\.example\b)[\w.*?-]*|secrets\/|[\w.-]+\.(pem|key|p12|pfx))(?=$|[\s"';|&)])/i;
// Commands that dump the environment, including interpreter one-liners.
const LEAKY_COMMANDS = /\bprintenv\b|(^|[;&|(]\s*)(env|set)\s*($|[|;&>])|\bexport\s+-p\b|(^|[;&|(]\s*)history\b/i;
const INTERPRETER_DUMP = /\b(node|python3?|ruby|perl|php)\s+-[ec]\b[^|;&]*(process\.env|os\.environ|\bENV\b)/i;
// Commands that read a whole directory tree and would pick up .env along the way.
const RECURSIVE_READ =
  /\b[ef]?grep\b[^|;&]*(\s-[a-zA-Z]*[rR][a-zA-Z]*\b|--recursive\b)|\b(rg|ag|ack)\b|\bfindstr\b[^|;&]*\/s\b|\bSelect-String\b[^|;&]*-Recurse|\bfind\b[^|;&]*-exec\s+(cat|head|tail|less|more|grep)\b|\bxargs\b[^|;&]*\b(cat|head|tail|less|more|grep|rg|sed|awk|type)\b|\bgit\s+grep\b[^|;&]*--no-index\b/i;
// A recursive read is allowed only when it explicitly excludes .env files.
const EXCLUDES_SECRETS = /(--exclude=|--glob[= ]|-g\s*)["']?!?\*?\.env/i;

const block = (why) => {
  process.stderr.write(
    `Blocked by project security policy: ${why}. ` +
      `Secrets stay in .env and are never read by the agent. ` +
      `Use .env.example for variable names, or ask the human.\n`
  );
  process.exit(2);
};

function check(raw) {
  if (!raw.trim()) block("empty hook payload (fail-closed)");

  let input;
  try {
    input = JSON.parse(raw);
  } catch {
    block("hook payload could not be parsed (fail-closed)");
  }

  const tool = input.tool_name ?? "";
  const ti = input.tool_input ?? {};
  // Normalize Windows paths so C:\repo\.env matches the same rule as C:/repo/.env.
  const targets = [ti.file_path, ti.path, ti.pattern, ti.glob, ti.command]
    .filter(Boolean)
    .map((t) => String(t).replace(/\\/g, "/"));

  for (const t of targets) {
    if (SECRET_PATH.test(t)) block(`${tool} touches a secret file (${t.slice(0, 80)})`);
  }

  if (tool === "Bash") {
    const cmd = String(ti.command ?? "");
    if (LEAKY_COMMANDS.test(cmd) || INTERPRETER_DUMP.test(cmd)) block("command would dump environment variables");
    // Check every command in a chain separately, so one excluded grep cannot hide an unexcluded one.
    for (const seg of cmd.split(/[;&|]+/)) {
      if (RECURSIVE_READ.test(seg) && !EXCLUDES_SECRETS.test(seg)) {
        block("recursive read without excluding .env (add --exclude='.env*' or -g '!.env*')");
      }
    }
  }

  process.exit(0);
}

// Read stdin as a stream: works with pipes on Windows, unlike readFileSync(0).
const chunks = [];
process.stdin.on("data", (c) => chunks.push(c));
process.stdin.on("error", () => block("cannot read hook payload (fail-closed)"));
process.stdin.on("end", () => {
  try {
    check(Buffer.concat(chunks).toString("utf8"));
  } catch (e) {
    block(`hook error (fail-closed): ${e.message}`);
  }
});