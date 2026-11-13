import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const KEY = "teamwork-status";
const REFRESH_MS = 5_000;
const MAX_LINES = 12;
const TITLE_MAX = 32;
const INSTANCE_MAX = 14;
const MODEL_MAX = 22;
const LANE_MAX = 3;
const WIDTH_MAX = 100;
const ENGINE = ["scripts", "teamwork.py"];

const STATE_ABBREV: Record<string, string> = {
  starting: "start",
  running: "run",
  exited: "done",
  failed: "fail",
  timeout: "tout",
  stopped: "stop",
  lost: "lost",
};

type Lane = {
  id?: string;
  instance?: string;
  role?: string;
  task?: string;
  state?: string;
  elapsed_text?: string;
  model?: string;
  provider?: string;
  attempt?: string;
};

type Instance = {
  instance?: string;
  role?: string;
  state?: string;
  task?: string;
  title?: string;
  elapsed_text?: string;
  progress_pct?: number | null;
  model?: string;
  provider?: string;
};

type Payload = {
  schema?: number;
  count?: number;
  instances?: Instance[];
  lanes?: Lane[];
  counts?: {
    busy?: number;
    idle?: number;
    ready?: number;
    review?: number;
    lanes?: number;
    activated?: number;
    retired?: number;
    lanes_live?: number;
    lanes_ended?: number;
  };
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

function stateAbbrev(value: string | undefined): string {
  const clean = (value ?? "").trim().toLowerCase();
  return STATE_ABBREV[clean] ?? (clean ? text(clean, 5) : "-");
}

function modelLabel(row: { model?: string; provider?: string }): string {
  const model = (row.model ?? "").trim();
  if (!model) return "host";
  const provider = (row.provider ?? "").trim();
  return text(provider ? `${provider}/${model}` : model, MODEL_MAX);
}

export function render(payload: Payload): string[] {
  const rows = (payload.instances ?? []).map((row) => ({
    instance: text(row.instance, INSTANCE_MAX) || "-",
    task: task_label(row.task),
    title: text(row.title, TITLE_MAX),
    elapsed: elapsed(row.elapsed_text),
    percent: row.progress_pct ?? null,
    model: modelLabel(row),
    busy: row.state === "busy",
  }));
  const lanes = (payload.lanes ?? []).map((lane) => ({
    id: text(lane.id, 8) || "-",
    instance: text(lane.instance, INSTANCE_MAX) || "-",
    task: task_label(lane.task),
    state: stateAbbrev(lane.state),
    live: lane.state === "starting" || lane.state === "running",
    elapsed: elapsed(lane.elapsed_text),
    model: modelLabel(lane),
  }));
  if (!rows.length && !lanes.length) return [];
  const busy = rows.filter((row) => row.busy);
  const idle = rows.filter((row) => !row.busy);
  const live = lanes.filter((lane) => lane.live);
  const counts = payload.counts ?? {};
  const review = counts.review ?? 0;
  const activated = counts.activated ?? rows.length;
  const lanesLive = counts.lanes_live ?? live.length;
  const header =
    `teamwork · ${activated} act · ${lanesLive} live · ` +
    `${busy.length} busy · ${review} review`;

  busy.sort((a, b) => (b.percent ?? -1) - (a.percent ?? -1) || a.instance.localeCompare(b.instance));
  const width = Math.min(INSTANCE_MAX, Math.max(0, ...busy.map((row) => row.instance.length)));
  const lines = [header];
  for (const lane of live.slice(0, LANE_MAX)) {
    lines.push(
      `⚙ ${lane.id} ${lane.instance} ${lane.task} ${lane.state} ${lane.elapsed} ${lane.model}`.trimEnd(),
    );
  }
  const room = MAX_LINES - lines.length - (idle.length ? 1 : 0);
  for (const row of busy.slice(0, Math.max(0, room))) {
    const tail = `${row.elapsed} ${bar(row.percent)} ${row.model}`.trimEnd();
    const fixed = `● ${row.instance.padEnd(width)} ${row.task}  ${tail}`.length;
    const budget = Math.min(TITLE_MAX, WIDTH_MAX - fixed);
    const title = budget > 0 ? text(row.title, budget) : "";
    const head = `● ${row.instance.padEnd(width)} ${row.task} ${title}`.trimEnd();
    lines.push(`${head}  ${tail}`.trimEnd());
  }
  const hidden = busy.length - Math.max(0, room);
  if (hidden > 0) lines.push(`  +${hidden} more busy`);
  if (idle.length) {
    lines.push(`○ idle: ${idle.length} (activated ${activated})`);
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
