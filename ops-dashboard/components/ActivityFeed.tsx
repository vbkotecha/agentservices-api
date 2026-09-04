import type { ActivityItem, ActivityType, SquadId } from "@/lib/board";
import { SQUAD_DOT, SQUAD_LABELS } from "@/lib/board";

const TYPE_LABELS: Record<ActivityType, string> = {
  health: "Health",
  ship: "Ship",
  pr: "PR",
  metric: "Metric",
  issue: "Issue",
  grant: "Grant",
  seo: "SEO",
  release: "Release",
};

const TYPE_COLORS: Record<ActivityType, string> = {
  health: "bg-ops-green-light text-ops-green",
  ship: "bg-ops-accent-light text-ops-accent",
  pr: "bg-ops-cyan-light text-ops-cyan",
  metric: "bg-ops-amber-light text-ops-amber",
  issue: "bg-ops-border-subtle text-ops-muted",
  grant: "bg-ops-green-light text-ops-green",
  seo: "bg-ops-cyan-light text-ops-cyan",
  release: "bg-ops-accent-light text-ops-accent",
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
  const squadLabel = SQUAD_LABELS[item.squad as SquadId];
  const dotColor = SQUAD_DOT[item.squad as SquadId];
  const typeColor = TYPE_COLORS[item.type];
  const typeLabel = TYPE_LABELS[item.type];

  return (
    <div className="flex gap-3 py-3 border-b border-ops-border-subtle last:border-0">
      <div className="min-w-0 flex-1">
        <p className="text-[13px] leading-snug text-ops-text">{item.message}</p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-medium ${typeColor}`}
          >
            {typeLabel}
          </span>
          <span className="inline-flex items-center gap-1 text-[10px] text-ops-muted">
            <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
            {squadLabel}
          </span>
          <span className="text-[10px] text-ops-muted">
            {formatRelative(item.timestamp)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ops-text">Activity</h2>
        <span className="text-xs text-ops-muted">{items.length} events</span>
      </div>
      <div className="flex-1 rounded-xl border border-ops-border bg-ops-surface shadow-card-sm">
        <div className="max-h-[520px] overflow-y-auto px-3 lg:max-h-none">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-xs text-ops-muted">No recent activity</p>
            </div>
          ) : (
            items.map((item) => <ActivityRow key={item.id} item={item} />)
          )}
        </div>
      </div>
    </section>
  );
}
