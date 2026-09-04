export type SquadId = "main-bot" | "distribution" | "radar" | "money-maker";

export type Priority = "critical" | "high" | "normal" | "low";

export type SquadStatus = "active" | "watch" | "idle";

export type KanbanColumn = "backlog" | "inFlight" | "done";

export type HumanColumn = "needsYou" | "waiting" | "done";

export type HumanOwner = "Vivek";

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
  description?: string;
  ownerId?: SquadId;
  updatedAt?: string;
}

export interface HumanCard {
  id: string;
  title: string;
  description: string;
  owner: HumanOwner;
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
  humanBoard: {
    needsYou: HumanCard[];
    waiting: HumanCard[];
    done: HumanCard[];
  };
  activity: ActivityItem[];
}

export const SQUAD_LABELS: Record<SquadId, string> = {
  "main-bot": "Main Bot",
  distribution: "Distribution",
  radar: "Radar",
  "money-maker": "Money Maker",
};

export const SQUAD_INITIALS: Record<SquadId, string> = {
  "main-bot": "MB",
  distribution: "DI",
  radar: "RA",
  "money-maker": "MM",
};

export const SQUAD_COLORS: Record<SquadId, string> = {
  "main-bot": "text-ops-accent bg-ops-accent-light",
  distribution: "text-ops-cyan bg-ops-cyan-light",
  radar: "text-ops-amber bg-ops-amber-light",
  "money-maker": "text-ops-green bg-ops-green-light",
};

export const SQUAD_DOT: Record<SquadId, string> = {
  "main-bot": "bg-ops-accent",
  distribution: "bg-ops-cyan",
  radar: "bg-ops-amber",
  "money-maker": "bg-ops-green",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  critical: "Critical",
  high: "High",
  normal: "Normal",
  low: "Low",
};

export const PRIORITY_CHIP: Record<Priority, string> = {
  critical: "bg-ops-red-light text-ops-red",
  high: "bg-ops-amber-light text-ops-amber",
  normal: "bg-ops-accent-light text-ops-accent",
  low: "bg-ops-border-subtle text-ops-muted",
};

export const COLUMN_STATUS: Record<KanbanColumn, { label: string; chip: string }> = {
  backlog: { label: "Backlog", chip: "bg-ops-border-subtle text-ops-secondary" },
  inFlight: { label: "In Flight", chip: "bg-ops-amber-light text-ops-amber" },
  done: { label: "Done", chip: "bg-ops-green-light text-ops-green" },
};

export const HUMAN_COLUMN_LABELS: Record<HumanColumn, string> = {
  needsYou: "Needs You",
  waiting: "Waiting",
  done: "Done",
};

export const HUMAN_COLUMN_CHIP: Record<HumanColumn, string> = {
  needsYou: "bg-ops-red-light text-ops-red",
  waiting: "bg-ops-amber-light text-ops-amber",
  done: "bg-ops-green-light text-ops-green",
};

import { readFile } from "fs/promises";
import path from "path";

export async function getBoardData(): Promise<BoardData> {
  const filePath = path.join(process.cwd(), "public", "board.json");
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as BoardData;
}
