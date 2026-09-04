import { ActivityFeed } from "@/components/ActivityFeed";
import { HumanActionsBoard } from "@/components/HumanActionsBoard";
import { KanbanBoard } from "@/components/KanbanBoard";
import { SquadStrip } from "@/components/SquadStrip";
import { TopBar } from "@/components/TopBar";
import { getBoardData } from "@/lib/board";

export default async function Home() {
  const board = await getBoardData();

  return (
    <div className="min-h-screen bg-ops-bg">
      <TopBar
        title={board.meta.title}
        updatedAt={board.meta.updatedAt}
        updatedBy={board.meta.updatedBy}
        health={board.health}
      />

      <main className="mx-auto max-w-7xl space-y-5 px-4 py-5 sm:px-6 sm:py-6">
        <SquadStrip squads={board.squads} />

        <HumanActionsBoard
          needsYou={board.humanBoard.needsYou}
          waiting={board.humanBoard.waiting}
          done={board.humanBoard.done}
        />

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_320px]">
          <KanbanBoard
            backlog={board.kanban.backlog}
            inFlight={board.kanban.inFlight}
            done={board.kanban.done}
          />
          <ActivityFeed items={board.activity} />
        </div>
      </main>

      <footer className="border-t border-ops-border py-4 text-center">
        <p className="text-[11px] text-ops-muted">
          Read-only · data from board.json · Yappa Ventures
        </p>
      </footer>
    </div>
  );
}
