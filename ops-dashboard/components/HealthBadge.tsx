import type { Health } from "@/lib/board";

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "America/Los_Angeles",
  });
}

export function HealthBadge({ health }: { health: Health }) {
  const isOk = health.status === "ok" && health.httpCode === 200;

  return (
    <div
      className={`flex items-center gap-3 rounded-lg border px-4 py-2.5 ${
        isOk
          ? "border-ops-green/30 bg-ops-green/5"
          : "border-ops-red/30 bg-ops-red/5"
      }`}
    >
      <span
        className={`relative flex h-2.5 w-2.5 ${isOk ? "" : "animate-pulse"}`}
      >
        <span
          className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
            isOk ? "animate-ping bg-ops-green" : "bg-ops-red"
          }`}
        />
        <span
          className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
            isOk ? "bg-ops-green" : "bg-ops-red"
          }`}
        />
      </span>
      <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
        <span className="font-mono text-sm font-medium">
          {health.httpCode} {health.version}
        </span>
        <span className="hidden text-ops-muted sm:inline">·</span>
        <span className="text-xs text-ops-muted">
          checked {formatTime(health.checkedAt)}
        </span>
      </div>
    </div>
  );
}
