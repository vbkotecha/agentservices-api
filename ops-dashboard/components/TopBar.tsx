"use client";

import { ThemeToggle } from "@/components/ThemeProvider";
import type { Health } from "@/lib/board";
import { HealthBadge } from "./HealthBadge";

interface TopBarProps {
  title: string;
  updatedAt: string;
  updatedBy: string;
  health: Health;
}

function formatUpdated(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
    timeZoneName: "short",
  });
}

export function TopBar({ title, updatedAt, updatedBy, health }: TopBarProps) {
  return (
    <header className="sticky top-0 z-10 border-b border-ops-border bg-ops-surface/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-ops-text">
            {title}
          </h1>
          <p className="mt-0.5 text-xs text-ops-muted">
            Updated {formatUpdated(updatedAt)} by {updatedBy}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <HealthBadge health={health} />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
