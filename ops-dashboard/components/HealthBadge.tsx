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
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
        isOk
          ? "border-ops-green/30 bg-ops-green-light text-ops-green"
          : "border-ops-red/30 bg-ops-red-light text-ops-red"
      }`}
    >
      <span
        className={`h-2 w-2 rounded-full ${isOk ? "bg-ops-green" : "bg-ops-red"}`}
      />
      <span className="font-medium">
        {isOk ? "Healthy" : "Degraded"}
      </span>
      <span className="text-xs opacity-75">
        {health.httpCode} · {health.version}
      </span>
      <span className="hidden text-xs opacity-60 sm:inline">
        · {formatTime(health.checkedAt)}
      </span>
    </div>
  );
}
