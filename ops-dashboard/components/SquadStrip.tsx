import type { Squad, SquadId } from "@/lib/board";
import { SQUAD_DOT, SQUAD_INITIALS, SQUAD_LABELS } from "@/lib/board";

const STATUS_LABEL: Record<string, string> = {
  active: "Active",
  watch: "Watching",
  idle: "Idle",
};

const STATUS_RING: Record<string, string> = {
  active: "ring-ops-green",
  watch: "ring-ops-amber",
  idle: "ring-ops-border",
};

function SquadAvatar({ squad }: { squad: Squad }) {
  const initials = SQUAD_INITIALS[squad.id as SquadId];
  const dotColor = SQUAD_DOT[squad.id as SquadId];
  const ringColor = STATUS_RING[squad.status];

  return (
    <div
      className="group relative flex flex-col items-center gap-1.5"
      title={`${squad.name}: ${squad.headline}`}
    >
      <div
        className={`relative flex h-10 w-10 items-center justify-center rounded-full bg-ops-surface border border-ops-border ring-2 ${ringColor} shadow-card-sm transition-shadow group-hover:shadow-card`}
      >
        <span className="text-xs font-semibold text-ops-secondary">
          {initials}
        </span>
        <span
          className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-ops-surface ${dotColor}`}
        />
      </div>
      <div className="text-center">
        <p className="text-[11px] font-medium text-ops-text leading-tight">
          {SQUAD_LABELS[squad.id as SquadId]}
        </p>
        <p className="text-[10px] text-ops-muted">{STATUS_LABEL[squad.status]}</p>
      </div>
    </div>
  );
}

export function SquadStrip({ squads }: { squads: Squad[] }) {
  return (
    <section className="rounded-xl border border-ops-border bg-ops-surface px-4 py-3 shadow-card-sm">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-medium text-ops-muted uppercase tracking-wide">
          Squads
        </p>
        <div className="flex flex-1 items-start justify-end gap-5 overflow-x-auto pb-1 sm:justify-center sm:gap-8">
          {squads.map((squad) => (
            <SquadAvatar key={squad.id} squad={squad} />
          ))}
        </div>
      </div>
    </section>
  );
}
