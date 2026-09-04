import type { ActivityItem, ActivityType, SquadId } from "@/lib/board";
import { SQUAD_COLORS, SQUAD_LABELS } from "@/lib/board";

const TYPE_ICONS: Record<ActivityType, string> = {
  health: "◉",
  ship: "▲",
  pr: "⎇",
  metric: "◎",
  issue: "#",
  grant: "$",
  seo: "◇",
  release: "★",
};

const TYPE_COLORS: Record<ActivityType, string> = {
  health: "text-ops-green",
  ship: "text-ops-accent",
  pr: "text-ops-cyan",
  metric: "text-ops-amber",
  issue: "text-ops-muted",
  grant: "text-ops-green",
  seo: "text-ops-cyan",
  release: "text-ops-accent",
};

function formatRelative(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const squadColor = SQUAD_COLORS[item.squad as SquadId];
  const squadLabel = SQUAD_LABELS[item.squad as SquadId];
  const typeColor = TYPE_COLORS[item.type];
  const icon = TYPE_ICONS[item.type];

  return (
    <div className="group flex gap-3 border-b border-ops-border/50 px-1 py-3 last:border-0 hover:bg-ops-elevated/30">
      <span
        className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded bg-ops-elevated font-mono text-xs ${typeColor}`}
      >
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug text-ops-text">{item.message}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <span className={`font-mono text-[10px] ${squadColor}`}>
            {squadLabel}
          </span>
          <span className="font-mono text-[10px] text-ops-muted">
            {formatRelative(item.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section>
      <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-ops-muted">
        Activity
      </h2>
      <div className="rounded-xl border border-ops-border bg-ops-surface/50">
        <div className="max-h-[480px] overflow-y-auto px-3">
          {items.map((item) => (
            <ActivityRow key={item.id} item={item} />
          ))}
        </div>
      </div>
    </section>
  );
}
