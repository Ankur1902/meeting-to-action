import { LayoutDashboard } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border px-6 py-16 text-center">
      <LayoutDashboard className="h-10 w-10 text-muted-foreground" />
      <h3 className="font-display text-lg">No tasks yet</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Paste meeting notes or upload a transcript above, then generate tasks to
        see your board come together.
      </p>
    </div>
  );
}
