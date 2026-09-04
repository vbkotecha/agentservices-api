import type { KanbanCard, KanbanColumn, SquadId } from "@/lib/board";
import {
  COLUMN_STATUS,
  PRIORITY_CHIP,
  PRIORITY_LABELS,
  SQUAD_DOT,
  SQUAD_LABELS,
} from "@/lib/board";

function formatRelative(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const hours = Math.floor(diff / 3_600_000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function StatusChip({ column }: { column: KanbanColumn }) {
  const { label, chip } = COLUMN_STATUS[column];
  return (
    <span className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-medium ${chip}`}>
      {label}
    </span>
  );
}

function Card({
  card,
  column,
}: {
  card: KanbanCard;
  column: KanbanColumn;
}) {
  const ownerId = (card.ownerId ?? card.squad) as SquadId;
  const ownerLabel = SQUAD_LABELS[ownerId];
  const dotColor = SQUAD_DOT[ownerId];
  const updatedAt = card.updatedAt ?? card.completedAt;

  return (
    <article
      className="group rounded-lg border border-ops-border bg-ops-surface p-3 shadow-card-sm transition-shadow hover:shadow-card"
    >
      <div className="flex items-start justify-between gap-2">
        {card.link ? (
          <a
            href={card.link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm font-medium leading-snug text-ops-text hover:text-ops-accent"
          >
            {card.title}
            <span className="ml-1 inline-block text-ops-muted opacity-0 transition-opacity group-hover:opacity-100">
              ↗
            </span>
          </a>
        ) : (
          <h4 className="text-sm font-medium leading-snug text-ops-text">
            {card.title}
          </h4>
        )}
        <StatusChip column={column} />
      </div>

      {card.description && (
        <p className="mt-1.5 text-xs leading-relaxed text-ops-secondary line-clamp-2">
          {card.description}
        </p>
      )}

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium text-ops-secondary`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
          {ownerLabel}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${PRIORITY_CHIP[card.priority]}`}
        >
          {PRIORITY_LABELS[card.priority]}
        </span>
        {card.tags.slice(0, 2).map((tag) => (
          <span
            key={tag}
            className="rounded bg-ops-bg px-1.5 py-0.5 text-[10px] text-ops-muted"
          >
            {tag}
          </span>
        ))}
      </div>

      {updatedAt && (
        <p className="mt-2 text-[10px] text-ops-muted">
          Updated {formatRelative(updatedAt)}
        </p>
      )}
    </article>
  );
}

interface ColumnProps {
  title: string;
  count: number;
  cards: KanbanCard[];
  column: KanbanColumn;
  emptyMessage: string;
}

function Column({ title, count, cards, column, emptyMessage }: ColumnProps) {
  return (
    <div className="flex min-h-[280px] flex-col rounded-xl border border-ops-border bg-ops-bg/50">
      <div className="flex items-center justify-between border-b border-ops-border px-3 py-2.5">
        <h3 className="text-xs font-semibold text-ops-secondary">{title}</h3>
        <span className="flex h-5 min-w-[20px] items-center justify-center rounded-md bg-ops-surface px-1.5 text-[11px] font-medium text-ops-muted shadow-card-sm">
          {count}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2">
        {cards.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
            <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-ops-surface border border-ops-border">
              <span className="text-ops-muted text-sm">—</span>
            </div>
            <p className="text-xs text-ops-muted">{emptyMessage}</p>
          </div>
        ) : (
          cards.map((card) => (
            <Card key={card.id} card={card} column={column} />
          ))
        )}
      </div>
    </div>
  );
}

interface KanbanBoardProps {
  backlog: KanbanCard[];
  inFlight: KanbanCard[];
  done: KanbanCard[];
}

export function KanbanBoard({ backlog, inFlight, done }: KanbanBoardProps) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ops-text">Mission Board</h2>
        <p className="text-xs text-ops-muted">
          {backlog.length + inFlight.length + done.length} items
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Column
          title="Backlog"
          count={backlog.length}
          cards={backlog}
          column="backlog"
          emptyMessage="Nothing queued yet"
        />
        <Column
          title="In Flight"
          count={inFlight.length}
          cards={inFlight}
          column="inFlight"
          emptyMessage="No active work"
        />
        <Column
          title="Done"
          count={done.length}
          cards={done}
          column="done"
          emptyMessage="No completed items"
        />
      </div>
    </section>
  );
}
