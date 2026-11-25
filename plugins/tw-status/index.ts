import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const ID = "tw-status";
export const SLOT = "home.footer.status";
export const REFRESH_MS = 2_000;
export const SCHEMA = 5;
export const BUDGET = 8;
const ENGINE = ["scripts", "teamwork.py"];
const HOST = "opencode";

export type Counts = {
  busy?: number;
  stalled?: number;
  idle?: number;
  ready?: number;
  review?: number;
  activated?: number;
  retired?: number;
  lanes?: number;
  lanes_live?: number;
  lanes_ended?: number;
};

export type Instance = {
  instance?: string;
  role?: string;
  state?: string;
  task?: string;
  stalled?: boolean;
  activity?: string;
};

export type Lane = {
  id?: string;
  instance?: string;
  task?: string;
  state?: string;
  elapsed_text?: string;
};

export type Status = {
  schema?: number;
  count?: number;
  counts?: Counts;
  instances?: Instance[];
  lanes?: Lane[];
};

export type Engine = { python: string; engine: string; project: string };

export type Context = {
  ui: {
    slot(input: { append: string; render: () => unknown }): () => void;
  };
};

export type StatusView = {
  element(): unknown;
  update(lines: string[]): void;
};

export type Definition = {
  id: string;
  setup(context: Context): (() => void) | void;
};

export type Exec = (
  file: string,
  args: string[],
  options: object,
  callback: (error: Error | null, stdout: string, stderr: string) => void,
) => unknown;

export type Deps = {
  exec?: Exec;
  schedule?: (fn: () => void, ms: number) => unknown;
  cancel?: (handle: unknown) => void;
  env?: Record<string, string | undefined>;
  engine?: Engine | null;
  width?: () => number;
};

function clip(value: string, width: number): string {
  const clean = value.replace(/\s+/g, " ").trim();
  if (clean.length <= width) return clean;
  return width <= 1 ? "…" : `${clean.slice(0, width - 1)}…`;
}

export function render(payload: Status | null, width = 100): string[] {
  if (!payload || payload.schema !== SCHEMA) return [];
  const limit = Number.isFinite(width) && width > 24 ? Math.floor(width) : 100;
  const counts = payload.counts ?? {};
  const head =
    `teamwork · ${counts.busy ?? 0} busy · ${counts.stalled ?? 0} stalled · ` +
    `${counts.idle ?? 0} idle · ${counts.activated ?? 0} staffed`;
  const lines = [clip(head, limit)];
  const lanes = payload.lanes ?? [];
  const live = lanes.filter((lane) => lane.state === "starting" || lane.state === "running");
  const liveCount = counts.lanes_live ?? live.length;
  if (liveCount > 0) {
    lines.push(clip(`${liveCount} live lane${liveCount === 1 ? "" : "s"}`, limit));
  }
  for (const lane of live.slice(0, BUDGET)) {
    lines.push(
      clip(
        `◇ ${lane.id ?? "-"} ${lane.instance ?? "-"} ${lane.task ?? "-"} ${lane.elapsed_text ?? ""}`.trimEnd(),
        limit,
      ),
    );
  }
  const stalled = (payload.instances ?? []).filter(
    (row) => row.stalled === true || row.state === "stalled",
  );
  for (const row of stalled.slice(0, BUDGET)) {
    lines.push(clip(`▲ ${row.instance ?? "-"} ${row.task ?? "-"}`.trimEnd(), limit));
  }
  return lines;
}

export function statusCommand(engine: Engine): { python: string; args: string[] } {
  return {
    python: engine.python,
    args: [engine.engine, "status", "--json", "--project", engine.project],
  };
}

function teamDir(start: string): string {
  let dir = resolve(start);
  for (let depth = 0; depth < 8; depth += 1) {
    if (existsSync(join(dir, ".pi", "Teamwork", "Teams"))) return dir;
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return resolve(start);
}

export function discoverEngine(env: Record<string, string | undefined>): Engine | null {
  const python = (env.TEAMWORK_PYTHON || "python3").trim() || "python3";
  const roots: string[] = [];
  if (env.TEAMWORK_ROOT) roots.push(resolve(env.TEAMWORK_ROOT));
  let dir = resolve(process.cwd());
  for (let depth = 0; depth < 8; depth += 1) {
    roots.push(dir);
    const parent = dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  roots.push(resolve(dirname(fileURLToPath(import.meta.url)), "..", ".."));
  for (const root of roots) {
    const engine = join(root, ...ENGINE);
    if (existsSync(engine)) return { python, engine, project: teamDir(root) };
  }
  return null;
}

export function readStatus(exec: Exec, cmd: { python: string; args: string[] }): Promise<Status | null> {
  return new Promise((settle) => {
    exec(cmd.python, cmd.args, { timeout: 4_000, maxBuffer: 4 << 20 }, (error, stdout) => {
      if (error) return settle(null);
      try {
        const parsed = JSON.parse(stdout) as Status;
        settle(parsed && parsed.schema === SCHEMA && Array.isArray(parsed.instances) ? parsed : null);
      } catch {
        settle(null);
      }
    });
  });
}

function hostAllows(env: Record<string, string | undefined>): boolean {
  const host = (env.TEAMWORK_AGENT_HOST || "").trim().toLowerCase();
  return host === "" || host === HOST;
}

export function defineStatusPlugin(
  createView: (context: Context) => StatusView,
  deps: Deps = {},
): Definition {
  const exec = deps.exec ?? execFile;
  const schedule = deps.schedule ?? setInterval;
  const cancel = deps.cancel ?? clearInterval;
  const env = deps.env ?? process.env;
  const width = deps.width ?? (() => {
    const columns = Number((process.stdout as { columns?: number }).columns);
    return Number.isFinite(columns) && columns > 24 ? Math.floor(columns) : 100;
  });
  return {
    id: ID,
    setup(context) {
      if (!hostAllows(env)) return;
      if (!context.ui) return;
      const view = createView(context);
      let payload: Status | null = null;
      const unclaim = context.ui.slot({ append: SLOT, render: () => view.element() });
      const tick = async (): Promise<void> => {
        const engine = deps.engine !== undefined ? deps.engine : discoverEngine(env);
        if (!engine) {
          view.update([]);
          return;
        }
        payload = await readStatus(exec, statusCommand(engine));
        view.update(render(payload, width()));
      };
      const timer = schedule(() => {
        void tick();
      }, REFRESH_MS);
      void tick();
      return () => {
        cancel(timer);
        unclaim();
        view.update([]);
      };
    },
  };
}

export default defineStatusPlugin(() => {
  let lines: string[] = [];
  return { element: () => lines, update: (next) => { lines = next; } };
});
