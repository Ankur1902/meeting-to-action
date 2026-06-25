import { FileText, ListChecks } from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import type { MeetingSummary } from "@/types/summary";

interface SummaryCardsProps {
  summary: MeetingSummary;
}

export function SummaryCards({ summary }: SummaryCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 animate-fade-in">
      <Card>
        <CardHeader className="flex-row items-center gap-2 space-y-0">
          <FileText className="h-4 w-4 text-accent" />
          <CardTitle className="text-base">Executive summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-foreground">
            {summary.executiveSummary}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex-row items-center gap-2 space-y-0">
          <ListChecks className="h-4 w-4 text-secondary" />
          <CardTitle className="text-base">Key decisions</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.keyDecisions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No explicit decisions captured.</p>
          ) : (
            <ul className="space-y-2">
              {summary.keyDecisions.map((decision, i) => (
                <li key={i} className="flex gap-2 text-sm leading-relaxed">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-secondary" />
                  {decision}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
