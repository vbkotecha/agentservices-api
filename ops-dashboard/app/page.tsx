import { ActivityFeed } from "@/components/ActivityFeed";
import { HealthBadge } from "@/components/HealthBadge";
import { KanbanBoard } from "@/components/KanbanBoard";
import { SquadStrip } from "@/components/SquadStrip";
import { getBoardData } from "@/lib/board";

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

export default async function Home() {
  const board = await getBoardData();

  return (
    <div className="ops-grid-bg min-h-screen">
      <header className="sticky top-0 z-10 border-b border-ops-border bg-ops-bg/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-lg font-bold tracking-tight">
                YAPPA
              </span>
              <span className="rounded bg-ops-accent/20 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-ops-accent">
                ops
              </span>
            </div>
            <p className="mt-0.5 text-xs text-ops-muted">
              Mission Control · updated {formatUpdated(board.meta.updatedAt)} by{" "}
              {board.meta.updatedBy}
            </p>
          </div>
          <HealthBadge health={board.health} />
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-8 px-4 py-6 sm:px-6 sm:py-8">
        <SquadStrip squads={board.squads} />

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
          <div className="xl:col-span-2">
            <KanbanBoard
              backlog={board.kanban.backlog}
              inFlight={board.kanban.inFlight}
              done={board.kanban.done}
            />
          </div>
          <div>
            <ActivityFeed items={board.activity} />
          </div>
        </div>
      </main>

      <footer className="border-t border-ops-border py-4 text-center">
        <p className="font-mono text-[10px] text-ops-muted">
          read-only v1 · data from board.json · Yappa Ventures
        </p>
      </footer>
    </div>
  );
}
