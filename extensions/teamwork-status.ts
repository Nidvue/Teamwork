import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const KEY = "teamwork-status";
const REFRESH_MS = 5_000;
const MAX_LINES = 12;
const TITLE_MAX = 32;
const INSTANCE_MAX = 14;
const ENGINE = ["scripts", "teamwork.py"];

type Instance = {
  instance?: string;
  role?: string;
  state?: string;
  task?: string;
  title?: string;
  elapsed_text?: string;
  progress_pct?: number | null;
};

type Payload = {
  schema?: number;
  count?: number;
  instances?: Instance[];
  counts?: { busy?: number; idle?: number; ready?: number; review?: number };
};

function ancestors(start: string): string[] {
  const out: string[] = [];
  let dir = resolve(start);
  for (let depth = 0; depth < 8; depth += 1) {
    out.push(dir);
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return out;
}

function findEngine(cwd: string): string | null {
  const env = process.env.TEAMWORK_ROOT;
  const roots = env ? [resolve(env), ...ancestors(cwd)] : ancestors(cwd);
  for (const root of roots) {
    const candidate = join(root, ...ENGINE);
    if (existsSync(candidate)) return candidate;
  }
  return null;
}

function readStatus(engine: string): Promise<Payload | null> {
  const python = process.env.TEAMWORK_PYTHON || "python3";
  return new Promise((settle) => {
    execFile(
      python,
      [engine, "status", "--json"],
      { timeout: 4_000, maxBuffer: 4 << 20 },
      (error, stdout) => {
        if (error) return settle(null);
        try {
          const parsed = JSON.parse(stdout) as Payload;
          settle(parsed && Array.isArray(parsed.instances) ? parsed : null);
        } catch {
          settle(null);
        }
      },
    );
  });
}

function text(value: string | undefined, max: number): string {
  const clean = (value ?? "").replace(/\s+/g, " ").trim();
  if (!clean) return "";
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean;
}

function bar(percent: number | null | undefined): string {
  if (typeof percent !== "number" || Number.isNaN(percent)) return "";
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));
  const filled = Math.round((clamped / 100) * 5);
  return `${"█".repeat(filled)}${"░".repeat(5 - filled)} ${String(clamped).padStart(3)}%`;
}

function task_label(value: string | undefined): string {
  const clean = text(value, 20);
  const review = /^[a-z-]+\/(T-\d+)$/.exec(clean);
  return review ? `\u21b3${review[1]}` : text(clean, 8) || "-";
}

function elapsed(value: string | undefined): string {
  return ((value ?? "").trim() || "-").padStart(6);
}

export function render(payload: Payload): string[] {
  const rows = (payload.instances ?? []).map((row) => ({
    instance: text(row.instance, INSTANCE_MAX) || "-",
    task: task_label(row.task),
    title: text(row.title, TITLE_MAX),
    elapsed: elapsed(row.elapsed_text),
    percent: row.progress_pct ?? null,
    busy: row.state === "busy",
  }));
  const busy = rows.filter((row) => row.busy);
  const idle = rows.filter((row) => !row.busy);
  const counts = payload.counts ?? {};
  const review = counts.review ?? 0;
  const header =
    `teamwork · ${payload.count ?? rows.length} instance(s) · ${busy.length} busy` +
    (review ? ` · ${review} in review` : "");

  busy.sort((a, b) => (b.percent ?? -1) - (a.percent ?? -1) || a.instance.localeCompare(b.instance));
  const width = Math.min(INSTANCE_MAX, Math.max(0, ...busy.map((row) => row.instance.length)));
  const lines = [header];
  const room = MAX_LINES - 1 - (idle.length ? 1 : 0);
  for (const row of busy.slice(0, Math.max(0, room))) {
    const head = `● ${row.instance.padEnd(width)} ${row.task} ${row.title}`.trimEnd();
    lines.push(`${head}  ${row.elapsed} ${bar(row.percent)}`.trimEnd());
  }
  const hidden = busy.length - Math.max(0, room);
  if (hidden > 0) lines.push(`  +${hidden} more busy`);
  if (idle.length) {
    const names = idle.slice(0, 6).map((row) => row.instance).join(", ");
    const rest = idle.length - Math.min(6, idle.length);
    lines.push(`○ idle: ${names}${rest > 0 ? ` +${rest}` : ""}`);
  }
  return lines.slice(0, MAX_LINES);
}

export default function teamworkStatus(pi: ExtensionAPI): void {
  let enabled = true;
  let timer: ReturnType<typeof setInterval> | null = null;
  let context: ExtensionContext | null = null;

  const clear = (ctx: ExtensionContext): void => {
    ctx.ui.setWidget(KEY, []);
    ctx.ui.setStatus(KEY, "");
  };

  const stop = (): void => {
    if (timer) clearInterval(timer);
    timer = null;
  };

  const refresh = async (): Promise<void> => {
    const ctx = context;
    if (!ctx) return;
    if (!enabled) return clear(ctx);
    const cwd = (ctx as { cwd?: string }).cwd ?? process.cwd();
    const engine = findEngine(cwd);
    if (!engine) {
      clear(ctx);
      stop();
      return;
    }
    const payload = await readStatus(engine);
    if (!payload) {
      ctx.ui.setStatus(KEY, "teamwork: status unavailable");
      return;
    }
    const rows = payload.instances ?? [];
    const busy = rows.filter((row) => row.state === "busy").length;
    try {
      ctx.ui.setWidget(KEY, render(payload));
    } catch {
      ctx.ui.setWidget(KEY, []);
    }
    ctx.ui.setStatus(KEY, `teamwork ${busy}/${payload.count ?? rows.length} busy`);
  };

  const start = (): void => {
    stop();
    void refresh();
    timer = setInterval(() => void refresh(), REFRESH_MS);
    if (typeof timer === "object" && timer && "unref" in timer) timer.unref();
  };

  pi.on("session_start", async (_event, ctx) => {
    context = ctx;
    start();
  });

  pi.on("session_shutdown", async (_event, ctx) => {
    stop();
    clear(ctx);
    context = null;
  });

  pi.registerCommand("teamwork-status", {
    description: "toggle the live teamwork agent widget",
    handler: async (_args: string, ctx: ExtensionContext) => {
      context = ctx;
      enabled = !enabled;
      if (enabled) {
        start();
        ctx.ui.notify("teamwork status: on", "info");
      } else {
        stop();
        clear(ctx);
        ctx.ui.notify("teamwork status: off", "info");
      }
    },
  });
}
