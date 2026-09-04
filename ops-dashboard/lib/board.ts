export type SquadId = "main-bot" | "distribution" | "radar" | "money-maker";

export type Priority = "critical" | "high" | "normal" | "low";

export type SquadStatus = "active" | "watch" | "idle";

export type ActivityType =
  | "health"
  | "ship"
  | "pr"
  | "metric"
  | "issue"
  | "grant"
  | "seo"
  | "release";

export interface Squad {
  id: SquadId;
  name: string;
  codename: string;
  status: SquadStatus;
  headline: string;
  details: string[];
  priority: Priority;
}

export interface Health {
  status: "ok" | "degraded" | "down";
  httpCode: number;
  version: string;
  endpoint: string;
  checkedAt: string;
}

export interface KanbanCard {
  id: string;
  title: string;
  squad: SquadId;
  tags: string[];
  priority: Priority;
  link?: string;
  completedAt?: string;
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  squad: SquadId;
  type: ActivityType;
  message: string;
}

export interface BoardData {
  meta: {
    title: string;
    updatedAt: string;
    updatedBy: string;
  };
  health: Health;
  squads: Squad[];
  kanban: {
    backlog: KanbanCard[];
    inFlight: KanbanCard[];
    done: KanbanCard[];
  };
  activity: ActivityItem[];
}

export const SQUAD_LABELS: Record<SquadId, string> = {
  "main-bot": "Main Bot",
  distribution: "Distribution",
  radar: "Radar",
  "money-maker": "Money Maker",
};

export const SQUAD_COLORS: Record<SquadId, string> = {
  "main-bot": "text-ops-accent",
  distribution: "text-ops-cyan",
  radar: "text-ops-amber",
  "money-maker": "text-ops-green",
};

export const PRIORITY_STYLES: Record<Priority, string> = {
  critical: "border-l-ops-red bg-ops-red/5",
  high: "border-l-ops-amber bg-ops-amber/5",
  normal: "border-l-ops-accent bg-ops-accent/5",
  low: "border-l-ops-muted bg-ops-muted/5",
};

import { readFile } from "fs/promises";
import path from "path";

export async function getBoardData(): Promise<BoardData> {
  const filePath = path.join(process.cwd(), "public", "board.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as BoardData;
}
