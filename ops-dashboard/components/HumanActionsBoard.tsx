import type { HumanCard, HumanColumn } from "@/lib/board";
import {
  HUMAN_COLUMN_CHIP,
  HUMAN_COLUMN_LABELS,
  PRIORITY_CHIP,
  PRIORITY_LABELS,
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

function HumanCardView({
  card,
  column,
}: {
  card: HumanCard;
  column: HumanColumn;
}) {
  const columnChip = HUMAN_COLUMN_CHIP[column];

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
        <span
          className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${columnChip}`}
        >
          {HUMAN_COLUMN_LABELS[column]}
        </span>
      </div>

      <p className="mt-1.5 text-xs leading-relaxed text-ops-secondary">
        {card.description}
      </p>

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
        <span className="inline-flex items-center gap-1 rounded bg-ops-amber-light px-1.5 py-0.5 text-[10px] font-medium text-ops-amber">
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-ops-amber/20 text-[9px] font-semibold">
            VK
          </span>
          {card.owner}
        </span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${PRIORITY_CHIP[card.priority]}`}
        >
          {PRIORITY_LABELS[card.priority]}
        </span>
      </div>

      {card.completedAt && (
        <p className="mt-2 text-[10px] text-ops-muted">
          Done {formatRelative(card.completedAt)}
        </p>
      )}
    </article>
  );
}

interface ColumnProps {
  title: string;
  count: number;
  cards: HumanCard[];
  column: HumanColumn;
  emptyMessage: string;
}

function Column({ title, count, cards, column, emptyMessage }: ColumnProps) {
  return (
    <div className="flex min-h-[200px] flex-col rounded-lg border border-ops-border bg-ops-bg/60">
      <div className="flex items-center justify-between border-b border-ops-border px-3 py-2.5">
        <h3 className="text-xs font-semibold text-ops-secondary">{title}</h3>
        <span className="flex h-5 min-w-[20px] items-center justify-center rounded-md bg-ops-surface px-1.5 text-[11px] font-medium text-ops-muted shadow-card-sm">
          {count}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2">
        {cards.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center py-8 text-center">
            <p className="text-xs text-ops-muted">{emptyMessage}</p>
          </div>
        ) : (
          cards.map((card) => (
            <HumanCardView key={card.id} card={card} column={column} />
          ))
        )}
      </div>
    </div>
  );
}

interface HumanActionsBoardProps {
  needsYou: HumanCard[];
  waiting: HumanCard[];
  done: HumanCard[];
}

export function HumanActionsBoard({
  needsYou,
  waiting,
  done,
}: HumanActionsBoardProps) {
  const total = needsYou.length + waiting.length + done.length;

  return (
    <section
      className="rounded-xl border-2 border-ops-amber/25 bg-gradient-to-br from-ops-amber-light/40 via-ops-surface to-ops-surface p-4 shadow-card-sm dark:from-ops-amber-light/10"
      aria-labelledby="human-actions-heading"
    >
      <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span
              className="flex h-6 w-6 items-center justify-center rounded-full bg-ops-amber/15 text-[10px] font-bold text-ops-amber"
              aria-hidden
            >
              VK
            </span>
            <h2
              id="human-actions-heading"
              className="text-sm font-semibold text-ops-text"
            >
              Your plate
            </h2>
            <span className="rounded bg-ops-amber-light px-1.5 py-0.5 text-[10px] font-medium text-ops-amber">
              Human Actions
            </span>
          </div>
          <p className="mt-0.5 text-xs text-ops-muted">
            One-action gates only you can clear — DNS, wallets, grants
          </p>
        </div>
        <p className="text-xs text-ops-muted">{total} items</p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Column
          title="Needs You"
          count={needsYou.length}
          cards={needsYou}
          column="needsYou"
          emptyMessage="Nothing blocking right now"
        />
        <Column
          title="Waiting"
          count={waiting.length}
          cards={waiting}
          column="waiting"
          emptyMessage="No pending follow-ups"
        />
        <Column
          title="Done"
          count={done.length}
          cards={done}
          column="done"
          emptyMessage="Nothing completed yet"
        />
      </div>
    </section>
  );
}
