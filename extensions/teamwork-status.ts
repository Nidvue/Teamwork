import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const KEY = "teamwork-status";
const REFRESH_MS = 2_000;
const BUDGET = 12;
const TITLE_MAX = 32;
const INSTANCE_MAX = 14;
const INSTANCE_MIN = 6;
const MODEL_MAX = 22;
const LANE_MAX = 3;
const WIDTH_MAX = 100;
const ACTIVITY_MAX = 240;
const TASK_MAX = 6;
const REVIEW_TASK_MAX = 7;
const ELAPSED_W = 6;
const BAR_W = 10;
const DROP_MODEL_BELOW = 80;
const DROP_BAR_BELOW = 72;
const DROP_ACTIVITY_BELOW = 56;
const BARE_BELOW = 32;
const ENGINE = ["scripts", "teamwork.py"];

const GLYPH = { busy: "●", lane: "⚙", idle: "○", review: "↳", run: "▶", pause: "⏸", fail: "✕" };

const LANE_STATE: Record<string, [string, string, string]> = {
  starting: [GLYPH.run, "run", "ok"],
  running: [GLYPH.run, "run", "ok"],
  stopped: [GLYPH.pause, "pause", "warn"],
  failed: [GLYPH.fail, "fail", "danger"],
  timeout: [GLYPH.fail, "fail", "danger"],
  lost: [GLYPH.fail, "fail", "danger"],
};

const COLOUR: Record<string, string> = { ok: "success", warn: "warning", danger: "error" };

export type Paint = { fg?: (token: string, value: string) => string };

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
  last?: string;
  last_at?: string;
  last_seconds?: number | null;
  lane?: string;
  lane_state?: string;
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
  if (typeof percent !== "number" || Number.isNaN(percent)) return " ".repeat(BAR_W);
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));
  const filled = Math.round((clamped / 100) * 5);
  return `${"█".repeat(filled)}${"░".repeat(5 - filled)} ${String(clamped).padStart(3)}%`;
}

function task_id(value: string | undefined): string {
  const clean = (value ?? "").trim();
  const tail = clean.includes("/") ? clean.slice(clean.lastIndexOf("/") + 1) : clean;
  return /^T-\d+$/.test(tail) ? tail : "";
}

function task_label(value: string | undefined, review: boolean): string {
  const id = task_id(value);
  if (id) return review ? `${GLYPH.review}${id}` : id;
  return text((value ?? "").trim().split("/").pop(), TASK_MAX) || "-";
}

function elapsed(value: string | undefined): string {
  return ((value ?? "").trim() || "-").padStart(ELAPSED_W);
}

function ago(seconds: number | null | undefined): string {
  if (typeof seconds !== "number" || Number.isNaN(seconds) || seconds < 0) return "";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h`;
}

function modelLabel(model: string | undefined): string {
  const clean = (model ?? "").trim();
  if (!clean) return "host";
  return text(clean.includes("/") ? clean.slice(clean.lastIndexOf("/") + 1) : clean, MODEL_MAX);
}

function tint(paint: Paint | undefined, token: string, value: string): string {
  const fg = paint?.fg;
  if (!fg || !value || token === "neutral") return value;
  try {
    return fg(COLOUR[token] ?? token, value);
  } catch {
    return value;
  }
}

type Row = {
  instance: string;
  review: boolean;
  task: string;
  activity: string;
  elapsed: string;
  bar: string;
  model: string;
  percent: number | null;
  busy: boolean;
};

type Layout = { pad: number; taskW: number; activity: number; bar: boolean; model: boolean; bare: boolean };

function layoutFor(rows: Row[], width: number): Layout {
  const widest = Math.max(INSTANCE_MIN, ...rows.map((row) => row.instance.length));
  const pad = Math.min(INSTANCE_MAX, widest);
  const taskW = rows.some((row) => row.review) ? REVIEW_TASK_MAX : TASK_MAX;
  const bare = width < BARE_BELOW;
  const model = !bare && width >= DROP_MODEL_BELOW;
  const showBar = !bare && width >= DROP_BAR_BELOW;
  const showActivity = !bare && width >= DROP_ACTIVITY_BELOW;
  const head = 2 + pad + 1 + taskW;
  const tail = 1 + ELAPSED_W + (showBar ? 1 + BAR_W : 0) + (model ? 1 + MODEL_MAX : 0);
  const activity = showActivity ? Math.max(0, width - head - tail - 1) : 0;
  return { pad, taskW, activity, bar: showBar, model, bare };
}

function rowLine(row: Row, layout: Layout, width: number, paint: Paint | undefined): string | null {
  const head = `${GLYPH.busy} ${row.instance.padEnd(layout.pad)} ${row.task.padEnd(layout.taskW)}`;
  const arrow = row.review ? 2 + layout.pad + 1 : -1;
  let line = head;
  if (layout.bare) {
    line = line.trimEnd();
  } else {
    const middle = layout.activity > 0 ? `${row.activity.slice(0, layout.activity).padEnd(layout.activity)} ` : "";
    const tail = [row.elapsed, layout.bar ? row.bar : "", layout.model ? row.model : ""]
      .filter((part) => part)
      .join(" ");
    line = `${head} ${middle}${tail}`.trimEnd();
  }
  if (line.length > width) return null;
  let out = line;
  if (arrow >= 0 && out[arrow] === GLYPH.review) {
    out = out.slice(0, arrow) + tint(paint, "warn", GLYPH.review) + out.slice(arrow + 1);
  }
  return tint(paint, "ok", out[0]) + out.slice(1);
}

function laneLine(lane: Lane, width: number, paint: Paint | undefined): string | null {
  const state = LANE_STATE[(lane.state ?? "").trim().toLowerCase()];
  const glyph = state ? state[0] : GLYPH.run;
  const word = state ? state[1] : text(lane.state, 5) || "-";
  const id = text(lane.id, 8) || "-";
  const instance = text(lane.instance, INSTANCE_MAX) || "-";
  const task = task_label(lane.task, false);
  const line = `${GLYPH.lane} ${id} ${instance} ${task} ${glyph} ${word} ${elapsed(lane.elapsed_text)} ${modelLabel(lane.model)}`
    .trimEnd();
  if (line.length > width) return null;
  const at = line.indexOf(` ${glyph} `) + 1;
  let out = line;
  if (state) out = out.slice(0, at) + tint(paint, state[2], glyph) + out.slice(at + 1);
  return tint(paint, "ok", out[0]) + out.slice(1);
}

export function render(payload: Payload, width = WIDTH_MAX, paint?: Paint): string[] {
  const bound = Number.isFinite(width) && width > 20 ? Math.floor(width) : WIDTH_MAX;
  const instances = payload.instances ?? [];
  const lanes = payload.lanes ?? [];
  if (!instances.length && !lanes.length) return [];
  const counts = payload.counts ?? {};
  const rows: Row[] = instances.map((row) => ({
    instance: text(row.instance, INSTANCE_MAX) || "-",
    review: (row.role ?? "").trim().toLowerCase() === "reviewer",
    task: task_label(row.task, (row.role ?? "").trim().toLowerCase() === "reviewer"),
    activity: text(row.last, ACTIVITY_MAX) || text(row.title, TITLE_MAX),
    elapsed: elapsed(row.elapsed_text),
    bar: bar(row.progress_pct),
    model: modelLabel(row.model),
    percent: typeof row.progress_pct === "number" ? row.progress_pct : null,
    busy: (row.state ?? "") === "busy",
  }));
  rows.sort((a, b) => (b.percent ?? -1) - (a.percent ?? -1) || a.instance.localeCompare(b.instance));
  const busy = rows.filter((row) => row.busy);
  const idle = rows.length - busy.length;
  const named = new Set(rows.map((row) => row.instance));
  const live = lanes.filter((lane) => lane.state === "starting" || lane.state === "running");
  const laneOnly = live.filter((lane) => !named.has(text(lane.instance, INSTANCE_MAX) || "-"));
  const busyCount = counts.busy ?? busy.length;
  const liveCount = counts.lanes_live ?? live.length;
  const reviewCount = counts.review ?? 0;
  const idleLine = idle ? 1 : 0;
  const cap = BUDGET - 1 - idleLine;
  let room = Math.min(busy.length, Math.max(0, cap));
  if (room < busy.length) room = Math.max(0, cap - 1);
  const layout = layoutFor(busy, bound);
  const drawn = busy.slice(0, room).map((row) => rowLine(row, layout, bound, paint)).filter((line) => line !== null);
  const hidden = busy.length - drawn.length;
  const lines = [text(`teamwork · ${busyCount} busy · ${liveCount} live · ${reviewCount} review`, bound)];
  lines.push(...drawn);
  if (hidden > 0) lines.push(`+${hidden} more busy`);
  if (idle) lines.push(text(`${GLYPH.idle} idle: ${idle}`, bound));
  const laneRoom = hidden > 0 ? 0 : Math.min(LANE_MAX, BUDGET - lines.length);
  for (const lane of laneOnly.slice(0, Math.max(0, laneRoom))) {
    const line = laneLine(lane, bound, paint);
    if (line) lines.push(line);
  }
  return lines;
}

export function footer(payload: Payload): string {
  const rows = payload.instances ?? [];
  const busy = payload.counts?.busy ?? rows.filter((row) => row.state === "busy").length;
  return `teamwork ${busy}/${payload.count ?? rows.length} busy`;
}

function terminalWidth(): number {
  const columns = Number((process.stdout as { columns?: number }).columns);
  return Number.isFinite(columns) && columns > 20 ? columns : WIDTH_MAX;
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
    const paint = (ctx.ui as { theme?: Paint }).theme;
    try {
      ctx.ui.setWidget(KEY, render(payload, terminalWidth(), paint));
    } catch {
      ctx.ui.setWidget(KEY, []);
    }
    ctx.ui.setStatus(KEY, footer(payload));
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
