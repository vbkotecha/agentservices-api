import type { Squad, SquadId } from "@/lib/board";
import { SQUAD_COLORS } from "@/lib/board";

const STATUS_DOT: Record<string, string> = {
  active: "bg-ops-green",
  watch: "bg-ops-amber",
  idle: "bg-ops-muted",
};

const PRIORITY_RING: Record<string, string> = {
  critical: "ring-ops-red/50",
  high: "ring-ops-amber/50",
  normal: "ring-ops-accent/30",
  low: "ring-ops-border",
};

function SquadCard({ squad }: { squad: Squad }) {
  const colorClass = SQUAD_COLORS[squad.id as SquadId];

  return (
    <div
      className={`group relative flex flex-col gap-2 rounded-xl border border-ops-border bg-ops-surface p-4 ring-1 transition-all hover:border-ops-accent/30 hover:bg-ops-elevated ${PRIORITY_RING[squad.priority]}`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${STATUS_DOT[squad.status]}`}
          />
          <span className="font-mono text-[10px] uppercase tracking-widest text-ops-muted">
            {squad.codename}
          </span>
        </div>
        {squad.priority === "critical" && (
          <span className="rounded bg-ops-red/20 px-1.5 py-0.5 font-mono text-[10px] uppercase text-ops-red">
            war
          </span>
        )}
      </div>

      <h3 className={`text-sm font-semibold ${colorClass}`}>{squad.name}</h3>
      <p className="text-sm leading-snug text-ops-text">{squad.headline}</p>

      <ul className="mt-1 space-y-0.5">
        {squad.details.map((detail) => (
          <li
            key={detail}
            className="font-mono text-[11px] text-ops-muted before:mr-1.5 before:text-ops-border before:content-['›']"
          >
            {detail}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SquadStrip({ squads }: { squads: Squad[] }) {
  return (
    <section>
      <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-ops-muted">
        Squads
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {squads.map((squad) => (
          <SquadCard key={squad.id} squad={squad} />
        ))}
      </div>
    </section>
  );
}
