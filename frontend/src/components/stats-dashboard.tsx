import { ClipboardList, CircleDot, CheckCircle2, Flame } from "lucide-react";

import { cn } from "@/lib/utils";

interface StatsDashboardProps {
  stats: {
    total: number;
    open: number;
    completed: number;
    highPriority: number;
  };
}

const STAT_CONFIG = [
  { key: "total", label: "Total tasks", icon: ClipboardList, accent: "text-foreground" },
  { key: "open", label: "Open tasks", icon: CircleDot, accent: "text-secondary" },
  { key: "completed", label: "Completed", icon: CheckCircle2, accent: "text-priority-low" },
  { key: "highPriority", label: "High priority", icon: Flame, accent: "text-priority-high" },
] as const;

export function StatsDashboard({ stats }: StatsDashboardProps) {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-4 animate-fade-in">
      {STAT_CONFIG.map(({ key, label, icon: Icon, accent }) => (
        <div key={key} className="flex items-center gap-3 bg-card px-5 py-4">
          <Icon className={cn("h-5 w-5", accent)} />
          <div>
            <p className="font-mono text-2xl font-medium leading-none">{stats[key]}</p>
            <p className="text-xs text-muted-foreground">{label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
