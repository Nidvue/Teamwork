/**
 * Live team-lane status for the pi footer and a widget above the editor.
 *
 * The engine already owns the truth: `teamwork.py lane list --json` reconciles
 * every lane record with its process, its outcome file and its budget. This
 * extension is a renderer only - it polls that command and draws it, so the
 * display cannot disagree with `lane status`. No lane is started or steered here;
 * parallelism is the engine's (`swarm run`), never the host's.
 *
 * Configuration (environment):
 *   TEAMWORK_CLI        exact command to run (default: <cwd>/scripts/teamwork.py)
 *   TEAMWORK_LANES_POLL poll interval in ms (default 2000, 0 disables the poll)
 *   TEAMWORK_TEAM       team name when several teams live in one repository
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execFile } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";

const STATUS_KEY = "teamwork-lanes";
const WIDGET_KEY = "teamwork-lanes";
const DEFAULT_POLL_MS = 2000;
const MAX_ROWS = 5;

type LaneRow = {
	id: string;
	agent: string;
	role: string;
	task: string;
	title: string;
	state: string;
	live: boolean;
	elapsed_seconds: number;
	minutes: number;
	seconds_left: number | null;
	attempt: number;
	attempts: number;
	verdict: string;
	note: string;
	error: string;
};

type Command = { file: string; args: string[] };

function resolveCli(cwd: string): Command | null {
	const configured = (process.env.TEAMWORK_CLI ?? "").trim();
	if (configured) {
		const parts = configured.split(/\s+/);
		return { file: parts[0], args: parts.slice(1) };
	}
	const local = path.join(cwd, "scripts", "teamwork.py");
	if (fs.existsSync(local)) {
		return { file: "python3", args: [local] };
	}
	return { file: "teamwork", args: [] };
}

function readLanes(command: Command, cwd: string): Promise<LaneRow[]> {
	const args = [...command.args, "--project", cwd, "lane", "list", "--all", "--json"];
	const team = (process.env.TEAMWORK_TEAM ?? "").trim();
	if (team) {
		args.splice(command.args.length, 0, "--team", team);
	}
	return new Promise((resolve) => {
		execFile(command.file, args, { cwd, timeout: 4000 }, (error, stdout) => {
			if (error) {
				resolve([]);
				return;
			}
			try {
				const parsed = JSON.parse(stdout) as LaneRow[];
				resolve(Array.isArray(parsed) ? parsed : []);
			} catch {
				resolve([]);
			}
		});
	});
}

function elapsed(seconds: number): string {
	const total = Math.max(Math.round(seconds), 0);
	const minutes = Math.floor(total / 60);
	const rest = total % 60;
	if (minutes >= 60) {
		return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}m`;
	}
	return minutes > 0 ? `${minutes}m${String(rest).padStart(2, "0")}s` : `${rest}s`;
}

function remaining(row: LaneRow): string {
	if (row.seconds_left === null) {
		return "";
	}
	return row.seconds_left > 0 ? `${Math.ceil(row.seconds_left / 60)}m left` : "over budget";
}

function stateColour(state: string, theme: { fg: (c: string, s: string) => string }): string {
	switch (state) {
		case "running":
			return theme.fg("accent", "●");
		case "starting":
			return theme.fg("muted", "◌");
		case "exited":
			return theme.fg("success", "✓");
		case "failed":
			return theme.fg("error", "✗");
		case "timeout":
			return theme.fg("warning", "◷");
		case "stopped":
			return theme.fg("muted", "■");
		default:
			return theme.fg("dim", "·");
	}
}

export default function (pi: ExtensionAPI) {
	let timer: ReturnType<typeof setInterval> | undefined;
	let polling = false;

	const stop = () => {
		if (timer) {
			clearInterval(timer);
			timer = undefined;
		}
	};

	const render = async (ctx: { cwd: string; ui: any }) => {
		if (polling) {
			return;
		}
		const command = resolveCli(ctx.cwd);
		if (!command) {
			return;
		}
		polling = true;
		try {
			const rows = await readLanes(command, ctx.cwd);
			const live = rows.filter((row) => row.live);
			const recent = rows
				.filter((row) => !row.live)
				.slice(-MAX_ROWS)
				.reverse();
			const theme = ctx.ui.theme;
			if (live.length === 0) {
				ctx.ui.setWidget(WIDGET_KEY, undefined);
				const ended = rows.filter((row) => row.state === "exited").length;
				ctx.ui.setStatus(
					STATUS_KEY,
					rows.length === 0
						? undefined
						: theme.fg("dim", `teamwork: ${ended} lane(s) ok, none running`),
				);
				return;
			}
			const lines = live.slice(0, MAX_ROWS).map((row) => {
				const budget = remaining(row);
				return [
					stateColour(row.state, theme),
					theme.fg("accent", row.id),
					theme.fg("text", row.agent.padEnd(12)),
					theme.fg("muted", row.task || "-"),
					theme.fg("dim", elapsed(row.elapsed_seconds)),
					budget ? theme.fg("muted", budget) : "",
				]
					.filter(Boolean)
					.join("  ");
			});
			if (live.length > MAX_ROWS) {
				lines.push(theme.fg("dim", `  … and ${live.length - MAX_ROWS} more lane(s)`));
			}
			const header = theme.fg(
				"muted",
				`# teamwork · ${live.length} lane(s) running${recent.length ? ` · last: ${recent[0].state}` : ""}`,
			);
			ctx.ui.setWidget(WIDGET_KEY, [header, ...lines], { placement: "belowEditor" });
			ctx.ui.setStatus(
				STATUS_KEY,
				theme.fg("accent", "⚡") + theme.fg("dim", ` ${live.length} lane(s)`),
			);
		} finally {
			polling = false;
		}
	};

	pi.on("session_start", async (_event, ctx) => {
		await render(ctx);
		const pollMs = Number(process.env.TEAMWORK_LANES_POLL ?? DEFAULT_POLL_MS);
		if (Number.isFinite(pollMs) && pollMs > 0) {
			timer = setInterval(() => {
				void render(ctx);
			}, pollMs);
		}
	});

	pi.on("session_shutdown", async (_event, ctx) => {
		stop();
		ctx.ui.setWidget(WIDGET_KEY, undefined);
		ctx.ui.setStatus(STATUS_KEY, undefined);
	});

	pi.registerCommand("lanes", {
		description: "Show the team's live lanes and the last one that ended",
		handler: async (_args, ctx) => {
			const command = resolveCli(ctx.cwd);
			if (!command) {
				ctx.ui.notify("teamwork: no CLI found (set TEAMWORK_CLI or run from the project)", "warning");
				return;
			}
			const rows = await readLanes(command, ctx.cwd);
			if (rows.length === 0) {
				ctx.ui.notify("teamwork: no lane record yet - start a wave with `swarm run`", "info");
				return;
			}
			const live = rows.filter((row) => row.live);
			const ended = rows.filter((row) => !row.live).slice(-3);
			const summary = [
				`live: ${live.length}`,
				...live.map((row) => `${row.id} ${row.agent} ${row.task} ${row.state} ${elapsed(row.elapsed_seconds)}`),
				`ended: ${ended.map((row) => `${row.id} ${row.state}${row.verdict ? ` ${row.verdict}` : ""}`).join(", ") || "none"}`,
			].join("\n");
			ctx.ui.notify(summary, "info");
		},
	});
}
