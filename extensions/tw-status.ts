import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const KEY = "tw-status";
const REFRESH_MS = 2_000;
const BUDGET = 12;
const TITLE_MAX = 32;
const INSTANCE_MAX = 15;
const INSTANCE_MIN = 6;
const MODEL_MAX = 20;
const LANE_MAX = 3;
const WIDTH_MAX = 100;
const ACTIVITY_MAX = 28;
const TASK_W = 7;
const USED_W = 5;
const LEFT_MIN = 4;
const LEFT_MAX = 5;
const SEP = "▸";
const DROP_MODEL_BELOW = 80;
const DROP_ACTIVITY_BELOW = 56;
const DROP_LEFT_BELOW = 48;
const BARE_BELOW = 32;
const ENGINE = ["scripts", "teamwork.py"];

const GLYPH = { busy: "●", stalled: "▲", lane: "◇", review: "↳", half: "◐", run: "▸", pause: "‖", fail: "✕" };

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
  elapsed_seconds?: number | null;
  budget_seconds?: number | null;
  remaining_seconds?: number | null;
  remaining_text?: string;
  activity?: string;
  stalled?: boolean;
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
    stalled?: number;
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

type Engine = { engine: string; project: string };

function teamDir(cwd: string): string | null {
  for (const dir of ancestors(cwd)) {
    if (existsSync(join(dir, ".pi", "Teamwork", "Teams"))) return dir;
  }
  return null;
}

function skillEngine(): string {
  return join(dirname(fileURLToPath(import.meta.url)), "..", "skills", "tw", ...ENGINE);
}

function findEngine(cwd: string): Engine | null {
  const env = process.env.TEAMWORK_ROOT;
  if (env) {
    const root = resolve(env);
    const pinned = join(root, ...ENGINE);
    if (existsSync(pinned)) return { engine: pinned, project: teamDir(cwd) ?? root };
  }
  for (const root of ancestors(cwd)) {
    const candidate = join(root, ...ENGINE);
    if (existsSync(candidate)) return { engine: candidate, project: root };
  }
  const skill = skillEngine();
  if (!existsSync(skill)) return null;
  return { engine: skill, project: teamDir(cwd) ?? cwd };
}

function readStatus(engine: string, project: string): Promise<Payload | null> {
  const python = process.env.TEAMWORK_PYTHON || "python3";
  return new Promise((settle) => {
    execFile(
      python,
      [engine, "status", "--json", "--project", project],
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

const WIDE =
  /[\u1100-\u115F\u2E80-\u303E\u3041-\u33FF\u3400-\u4DBF\u4E00-\u9FFF\uA000-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/;

function cells(value: string): number {
  let total = 0;
  for (const char of value) total += WIDE.test(char) ? 2 : 1;
  return total;
}

function sliceCells(value: string, max: number): string {
  let out = "";
  let used = 0;
  for (const char of value) {
    const width = WIDE.test(char) ? 2 : 1;
    if (used + width > max) break;
    out += char;
    used += width;
  }
  return out;
}

function pad(value: string, width: number): string {
  const short = width - cells(value);
  return short > 0 ? `${value}${" ".repeat(short)}` : value;
}

function padStart(value: string, width: number): string {
  const short = width - cells(value);
  return short > 0 ? `${" ".repeat(short)}${value}` : value;
}

function text(value: string | undefined, max: number): string {
  const clean = (value ?? "").replace(/\s+/g, " ").trim();
  if (!clean) return "";
  return cells(clean) > max ? `${sliceCells(clean, max - 1)}…` : clean;
}

function clipWords(value: string | undefined, max: number): string {
  if (max <= 0) return "";
  const clean = (value ?? "").replace(/\s+/g, " ").trim();
  if (!clean) return "";
  if (cells(clean) <= max) return clean;
  if (max === 1) return "…";
  const cut = sliceCells(clean, max - 1);
  const space = cut.lastIndexOf(" ");
  const body = space > 0 ? cut.slice(0, space) : cut;
  return `${body.trimEnd()}…`;
}

function clock(seconds: number): string {
  const whole = Math.max(0, Math.round(seconds));
  if (whole < 60) return `${whole}s`;
  if (whole < 3600) {
    const minutes = Math.floor(whole / 60);
    return minutes >= 10 ? `${minutes}m` : `${minutes}m${String(whole % 60).padStart(2, "0")}s`;
  }
  return `${Math.floor(whole / 3600)}h${String(Math.floor((whole % 3600) / 60)).padStart(2, "0")}m`;
}

function secondsOf(value: number | null | undefined): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function usedClock(row: Instance): string {
  const seconds = secondsOf(row.elapsed_seconds);
  if (seconds !== null) return clock(seconds);
  return (row.elapsed_text ?? "").trim() || "-";
}

function leftClock(row: Instance): string {
  const remaining = secondsOf(row.remaining_seconds);
  if (remaining !== null) return clock(Math.max(0, remaining));
  const budget = secondsOf(row.budget_seconds);
  const elapsed = secondsOf(row.elapsed_seconds);
  if (budget !== null && budget > 0 && elapsed !== null) return clock(Math.max(0, budget - elapsed));
  return "-";
}

function task_id(value: string | undefined): string {
  const clean = (value ?? "").trim();
  const tail = clean.includes("/") ? clean.slice(clean.lastIndexOf("/") + 1) : clean;
  return /^T-\d+$/.test(tail) ? tail : "";
}

function task_label(value: string | undefined, review: boolean): string {
  const id = task_id(value);
  if (id) return review ? `${GLYPH.review}${id}` : id;
  return text((value ?? "").trim().split("/").pop(), TASK_W) || "-";
}

function elapsed(value: string | undefined): string {
  return ((value ?? "").trim() || "-").padStart(USED_W);
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
  state: string;
  stalled: boolean;
  review: boolean;
  task: string;
  used: string;
  left: string;
  body: string;
  age: string;
  model: string;
};

type Layout = {
  pad: number;
  taskW: number;
  leftW: number;
  activity: number;
  left: boolean;
  model: boolean;
  bare: boolean;
};

function rowFrom(row: Instance): Row {
  const role = (row.role ?? "").trim().toLowerCase();
  const review = role === "reviewer";
  const stalled = row.stalled === true || (row.state ?? "").trim().toLowerCase() === "stalled";
  const state = (row.state ?? "").trim().toLowerCase() || (stalled ? "stalled" : "busy");
  const age = ago(secondsOf(row.last_seconds));
  const core =
    clipWords(row.activity, ACTIVITY_MAX) || clipWords(row.last, ACTIVITY_MAX) || text(row.title, TITLE_MAX);
  const word = state === "busy" ? "" : state;
  const body = word ? [word, core].filter((part) => part).join(" · ") : core;
  return {
    instance: (row.instance ?? "").trim() || "-",
    state,
    stalled,
    review,
    task: task_label(row.task, review),
    used: usedClock(row),
    left: stalled ? "-" : leftClock(row),
    body,
    age,
    model: modelLabel(row.model),
  };
}

function layoutFor(rows: Row[], width: number): Layout {
  const widest = Math.max(INSTANCE_MIN, ...rows.map((row) => cells(row.instance)));
  const pad = Math.min(INSTANCE_MAX, widest);
  const bare = width < BARE_BELOW;
  const model = !bare && width >= DROP_MODEL_BELOW;
  const left = !bare && width >= DROP_LEFT_BELOW;
  const showActivity = !bare && width >= DROP_ACTIVITY_BELOW;
  const leftW = Math.min(LEFT_MAX, Math.max(LEFT_MIN, ...rows.map((row) => row.left.length)));
  const head = 2 + pad + 1 + TASK_W;
  const tail =
    1 +
    USED_W +
    (left ? 2 + 1 + leftW : 0) +
    (model ? 1 + MODEL_MAX : 0);
  const room = showActivity ? Math.max(0, width - head - tail - 1) : 0;
  const activity = Math.min(ACTIVITY_MAX, room);
  return { pad, taskW: TASK_W, leftW, activity, left, model, bare };
}

function fitActivity(body: string, age: string, room: number): string {
  if (room <= 0) return "";
  const full = body && age ? `${body} · ${age}` : body || age;
  if (full.length <= room) return full;
  return clipWords(body || age, room);
}

function rowLine(row: Row, layout: Layout, width: number, paint: Paint | undefined): string | null {
  const glyph = row.stalled ? GLYPH.stalled : row.review ? GLYPH.half : GLYPH.busy;
  const head = `${glyph} ${pad(row.instance, layout.pad)} ${pad(row.task, layout.taskW)}`;
  if (layout.bare) {
    const bare = head.trimEnd();
    if (cells(bare) > width) return null;
    return tint(paint, row.stalled ? "warn" : "ok", bare[0]) + bare.slice(1);
  }
  const cols = [head, padStart(row.used, USED_W)];
  const blankLeft = row.stalled;
  const leftCell = blankLeft ? " ".repeat(SEP.length + 1 + layout.leftW) : `${SEP} ${padStart(row.left, layout.leftW)}`;
  if (layout.left) cols.push(leftCell);
  let line = cols.join(" ");
  const tail = layout.model && row.model ? ` ${row.model}` : "";
  if (layout.activity) {
    const room = Math.min(layout.activity, width - cells(line) - cells(tail) - 1);
    const cell = fitActivity(row.body, row.age, room);
    if (cell) line = `${line} ${cell}`;
  }
  line = `${line}${tail}`.trimEnd();
  if (cells(line) > width) return null;
  return tint(paint, row.stalled ? "warn" : "ok", line[0]) + line.slice(1);
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
  if (cells(line) > width) return null;
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
  const rows: Row[] = instances.map(rowFrom);
  rows.sort((a, b) => a.instance.localeCompare(b.instance));
  const drawable = rows.filter((row) => row.state !== "idle");
  const named = new Set(rows.map((row) => row.instance));
  const live = lanes.filter((lane) => lane.state === "starting" || lane.state === "running");
  const laneOnly = live.filter((lane) => !named.has((lane.instance ?? "").trim() || "-"));
  const liveCount = counts.lanes_live ?? live.length;
  const reviewCount = counts.review ?? 0;
  const header: string[] = [];
  if (liveCount) header.push(`${liveCount} live`);
  if (reviewCount) header.push(`${reviewCount} review`);
  const cap = BUDGET - 1;
  let room = Math.min(drawable.length, Math.max(0, cap));
  if (room < drawable.length) room = Math.max(0, cap - 1);
  const layout = layoutFor(drawable, bound);
  const drawn = drawable
    .slice(0, room)
    .map((row) => rowLine(row, layout, bound, paint))
    .filter((line) => line !== null);
  const hidden = drawable.length - drawn.length;
  const head = header.length ? `teamwork · ${header.join(" · ")}` : "teamwork";
  const lines = [text(head, bound)];
  lines.push(...drawn);
  if (hidden > 0) lines.push(`+${hidden} more busy`);
  const laneRoom = hidden > 0 ? 0 : Math.min(LANE_MAX, BUDGET - lines.length);
  for (const lane of laneOnly.slice(0, Math.max(0, laneRoom))) {
    const line = laneLine(lane, bound, paint);
    if (line) lines.push(line);
  }
  return lines;
}

function terminalWidth(): number {
  const columns = Number((process.stdout as { columns?: number }).columns);
  return Number.isFinite(columns) && columns > 20 ? columns : WIDTH_MAX;
}

export default function teamworkStatus(pi: ExtensionAPI): void {
  let enabled = true;
  let timer: ReturnType<typeof setInterval> | null = null;
  let context: ExtensionContext | null = null;

  const stop = (): void => {
    if (timer) clearInterval(timer);
    timer = null;
  };

  const stale = (): void => {
    stop();
    context = null;
  };

  const live = (ctx: ExtensionContext): boolean => {
    try {
      void ctx.ui;
      return true;
    } catch {
      stale();
      return false;
    }
  };

  const clear = (ctx: ExtensionContext): void => {
    try {
      ctx.ui.setWidget(KEY, []);
      ctx.ui.setStatus(KEY, "");
    } catch {
      stale();
    }
  };

  const refresh = async (): Promise<void> => {
    const ctx = context;
    if (!ctx) return;
    if (!live(ctx)) return;
    try {
      if (!enabled) {
        clear(ctx);
        return;
      }
      const cwd = (ctx as { cwd?: string }).cwd ?? process.cwd();
      const engine = findEngine(cwd);
      if (!engine) {
        clear(ctx);
        return;
      }
      const payload = await readStatus(engine.engine, engine.project);
      if (!payload) {
        ctx.ui.setWidget(KEY, [`${GLYPH.stalled} teamwork: status unavailable`]);
        return;
      }
      const paint = (ctx.ui as { theme?: Paint }).theme;
      ctx.ui.setWidget(KEY, render(payload, terminalWidth(), paint));
    } catch {
      stop();
      clear(ctx);
    }
  };

  const tick = (): void => {
    void refresh().catch(stop);
  };

  const start = (): void => {
    stop();
    timer = setInterval(tick, REFRESH_MS);
    if (typeof timer === "object" && timer && "unref" in timer) timer.unref();
    tick();
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

  pi.registerCommand("tw-status", {
    description: "toggle the live teamwork agent widget",
    handler: async (_args: string, ctx: ExtensionContext) => {
      if (!live(ctx)) return;
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
