import type { KanbanCard, SquadId } from "@/lib/board";
import { PRIORITY_STYLES, SQUAD_COLORS, SQUAD_LABELS } from "@/lib/board";

function Card({ card }: { card: KanbanCard }) {
  const squadColor = SQUAD_COLORS[card.squad as SquadId];
  const squadLabel = SQUAD_LABELS[card.squad as SquadId];

  return (
    <div
      className={`rounded-lg border border-ops-border border-l-[3px] p-3 transition-colors hover:bg-ops-elevated/50 ${PRIORITY_STYLES[card.priority]}`}
    >
      {card.link ? (
        <a
          href={card.link}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-sm font-medium leading-snug text-ops-text hover:text-ops-accent"
        >
          {card.title}
          <span className="ml-1 text-ops-muted">↗</span>
        </a>
      ) : (
        <p className="text-sm font-medium leading-snug text-ops-text">
          {card.title}
        </p>
      )}

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className={`font-mono text-[10px] ${squadColor}`}>
          {squadLabel}
        </span>
        {card.tags.map((tag) => (
          <span
            key={tag}
            className="rounded bg-ops-elevated px-1.5 py-0.5 font-mono text-[10px] text-ops-muted"
          >
            {tag}
          </span>
        ))}
      </div>

      {card.completedAt && (
        <p className="mt-1.5 font-mono text-[10px] text-ops-muted">
          ✓{" "}
          {new Date(card.completedAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })}
        </p>
      )}
    </div>
  );
}

interface ColumnProps {
  title: string;
  count: number;
  cards: KanbanCard[];
  accent?: string;
}

function Column({ title, count, cards, accent = "text-ops-muted" }: ColumnProps) {
  return (
    <div className="flex min-h-[200px] flex-col rounded-xl border border-ops-border bg-ops-surface/50">
      <div className="flex items-center justify-between border-b border-ops-border px-4 py-3">
        <h3 className={`font-mono text-xs uppercase tracking-widest ${accent}`}>
          {title}
        </h3>
        <span className="rounded-full bg-ops-elevated px-2 py-0.5 font-mono text-[10px] text-ops-muted">
          {count}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3">
        {cards.length === 0 ? (
          <p className="py-8 text-center text-xs text-ops-muted">Empty</p>
        ) : (
          cards.map((card) => <Card key={card.id} card={card} />)
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
      <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-ops-muted">
        Mission Board
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Column title="Backlog" count={backlog.length} cards={backlog} />
        <Column
          title="In Flight"
          count={inFlight.length}
          cards={inFlight}
          accent="text-ops-amber"
        />
        <Column
          title="Done"
          count={done.length}
          cards={done}
          accent="text-ops-green"
        />
      </div>
    </section>
  );
}
