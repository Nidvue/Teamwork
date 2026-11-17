import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { isAbsolute, join, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const KEY = "teamwork-bus";
const BUS = [".pi", "Teamwork", "Bus"];
const CLAIMS = "claims";
const WRITE_TOOLS = new Set(["write", "edit"]);
const PRIORITY: Record<string, number> = { urgent: 0, high: 1, normal: 2, low: 3 };
const DEAD = new Set(["released", "closed", "taken", "done", "cancelled"]);
const SHOW = 8;

export type Mail = {
  id?: string;
  from?: string;
  to?: string;
  subject?: string;
  body?: string;
  priority?: string;
  created?: string;
  state?: string;
  expires?: string;
  scope?: string;
  sender_session?: string;
};

export type Claim = {
  id?: string;
  path?: string;
  task?: string;
  area?: string;
  by?: string;
  session?: string;
  root?: string;
  created?: string;
  expires?: string;
  state?: string;
};

function ancestors(start: string): string[] {
  const out: string[] = [];
  let dir = resolve(start);
  for (let depth = 0; depth < 8; depth += 1) {
    out.push(dir);
    const parent = resolve(dir, "..");
    if (parent === dir) break;
    dir = parent;
  }
  return out;
}

function cwdOf(ctx: ExtensionContext | undefined): string {
  const value = (ctx as { cwd?: string } | undefined)?.cwd;
  return typeof value === "string" && value ? value : process.cwd();
}

export function projectRoot(cwd: string, env: NodeJS.ProcessEnv = process.env): string {
  const set = (env.TEAMWORK_ROOT || "").trim();
  if (set) return resolve(set);
  for (const dir of ancestors(cwd)) {
    if (existsSync(join(dir, ...BUS))) return dir;
  }
  return resolve(cwd);
}

export function busRoot(root: string, env: NodeJS.ProcessEnv = process.env): string {
  const set = (env.TEAMWORK_BUS || "").trim();
  return set ? resolve(set) : join(resolve(root), ...BUS);
}

export function sessionId(env: NodeJS.ProcessEnv = process.env): string {
  return (env.PI_SESSION_ID || "").trim();
}

export function parseAddress(value: string): string | null {
  const clean = (value || "").trim();
  if (clean === "*") return "*";
  const match = /^(role|team|session):(.+)$/.exec(clean);
  if (!match) return null;
  const body = match[2].trim();
  return body ? `${match[1]}:${body}` : null;
}

export function addresses(env: NodeJS.ProcessEnv = process.env): string[] {
  const out = ["*"];
  const role = (env.TEAMWORK_ROLE || "").trim();
  const team = (env.TEAMWORK_TEAM || "").trim();
  const session = sessionId(env);
  if (role) out.push(`role:${role}`);
  if (team) out.push(`team:${team}`);
  if (session) out.push(`session:${session}`);
  return out;
}

function readJson(path: string): Record<string, unknown> | null {
  try {
    const parsed = JSON.parse(readFileSync(path, "utf-8"));
    return parsed && typeof parsed === "object" ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function records(dir: string): Record<string, unknown>[] {
  if (!existsSync(dir)) return [];
  const out: Record<string, unknown>[] = [];
  for (const file of readdirSync(dir)) {
    if (!file.endsWith(".json")) continue;
    const row = readJson(join(dir, file));
    if (row) out.push({ ...row, id: String(row.id || file.replace(/\.json$/, "")) });
  }
  return out;
}

export function live(record: { expires?: string; state?: string }, now = Date.now()): boolean {
  const state = (record.state || "").trim().toLowerCase();
  if (DEAD.has(state)) return false;
  const stamp = Date.parse((record.expires || "").trim());
  return !Number.isFinite(stamp) || stamp > now;
}

function rank(row: { priority?: string }): number {
  return PRIORITY[(row.priority || "normal").trim().toLowerCase()] ?? 2;
}

export function pendingMail(
  root: string,
  keys: string[] = addresses(),
  now = Date.now(),
): (Mail & { key?: string })[] {
  const bus = busRoot(root);
  const seen = new Map<string, Mail & { key?: string }>();
  for (const key of keys) {
    for (const row of records(join(bus, key))) {
      const mail = row as Mail;
      if ((mail.state || "pending").trim().toLowerCase() !== "pending") continue;
      if (!live(mail, now)) continue;
      const id = String(mail.id || "");
      if (!id || seen.has(id)) continue;
      seen.set(id, { ...mail, key });
    }
  }
  return [...seen.values()].sort(
    (a, b) => rank(a) - rank(b) || String(a.created || "").localeCompare(String(b.created || "")),
  );
}

export function mailText(rows: Mail[]): string {
  const lines = [`teamwork bus: ${rows.length} pending message(s)`];
  for (const row of rows.slice(0, SHOW)) {
    const priority = (row.priority || "normal").trim().toLowerCase();
    lines.push(`- ${row.id} from ${row.from || "?"} [${priority}] ${row.subject || "(no subject)"}`);
    const body = (row.body || "").replace(/\s+/g, " ").trim();
    if (body) lines.push(`  ${body.slice(0, 200)}`);
  }
  if (rows.length > SHOW) lines.push(`  +${rows.length - SHOW} more`);
  return lines.join("\n");
}

export function claims(bus: string): Claim[] {
  return records(join(bus, CLAIMS)) as Claim[];
}

export function holder(bus: string, path: string, session = "", now = Date.now()): Claim | null {
  const target = resolve(path);
  for (const claim of claims(bus)) {
    if (!claim.path) continue;
    if (session && claim.session && claim.session === session) continue;
    if (!live(claim, now)) continue;
    const raw = claim.path;
    const base = (claim.root || "").trim();
    const absolute = isAbsolute(raw) ? resolve(raw) : resolve(base || ".", raw);
    if (absolute === target) return claim;
  }
  return null;
}

export function writeTarget(tool: string, input: Record<string, unknown> | undefined): string | null {
  if (!WRITE_TOOLS.has((tool || "").trim())) return null;
  const value = input?.path;
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

const DELIVERED = new Map<string, Set<string>>();

function delivered(session: string): Set<string> {
  let seen = DELIVERED.get(session);
  if (!seen) {
    seen = new Set<string>();
    DELIVERED.set(session, seen);
  }
  return seen;
}

function take(bus: string, rows: (Mail & { key?: string })[], session: string): void {
  for (const row of rows) {
    const key = row.key || "";
    if (!key.startsWith("session:")) continue;
    const path = join(bus, key, `${row.id}.json`);
    const row_ = readJson(path);
    if (!row_) continue;
    writeFileSync(
      path,
      JSON.stringify({ ...row_, state: "taken", taken_by: session }, null, 2) + "\n",
      "utf-8",
    );
  }
}

export default function teamworkBus(pi: ExtensionAPI): void {
  pi.on("session_start", async (_event, ctx) => {
    const session = sessionId();
    if (!session) return;
    const bus = busRoot(projectRoot(cwdOf(ctx)));
    mkdirSync(join(bus, `session:${session}`), { recursive: true });
  });

  pi.on("before_agent_start", async (_event, ctx) => {
    const root = projectRoot(cwdOf(ctx));
    const session = sessionId();
    const seen = delivered(session);
    const rows = pendingMail(root, addresses()).filter((row) => !seen.has(String(row.id || "")));
    if (!rows.length) return;
    pi.sendMessage({ customType: KEY, content: mailText(rows) }, { deliverAs: "nextTurn" });
    for (const row of rows) seen.add(String(row.id || ""));
    take(busRoot(root), rows, session);
  });

  pi.on("tool_call", async (event, ctx) => {
    const target = writeTarget(event.toolName, (event.input ?? {}) as Record<string, unknown>);
    if (!target) return;
    const cwd = cwdOf(ctx);
    const absolute = isAbsolute(target) ? resolve(target) : resolve(cwd, target);
    const hit = holder(busRoot(projectRoot(cwd)), absolute, sessionId());
    if (!hit) return;
    const until = (hit.expires || "").trim();
    const reason = `refused: ${absolute} is claimed by ${hit.by || "another session"} (${
      hit.id || "claim"
    })${until ? ` until ${until}` : ""}`;
    return { block: true, reason };
  });
}
