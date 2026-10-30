"use client";

import { useEffect, useState } from "react";
import { Clock, Copy, GitCompare } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getInsights } from "@/services/api";
import type { Insights } from "@/types/agent";

interface InsightsPanelProps {
  /** Changes when a new meeting is stored, triggering a refetch. */
  refreshKey: string | null;
}

/** Cross-meeting signals: overdue carry-overs, duplicates and conflicts. */
export function InsightsPanel({ refreshKey }: InsightsPanelProps) {
  const [insights, setInsights] = useState<Insights | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getInsights()
      .then((data) => {
        if (!cancelled) {
          setInsights(data);
          setUnavailable(false);
        }
      })
      .catch(() => !cancelled && setUnavailable(true));
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const empty =
    insights && !insights.overdue.length && !insights.duplicates.length && !insights.conflicts.length;

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <GitCompare className="h-4 w-4 text-secondary" />
        <CardTitle className="text-base">Across your meetings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {unavailable && <p className="text-muted-foreground">Insights unavailable — is the backend running?</p>}
        {empty && <p className="text-muted-foreground">No overdue, duplicate or conflicting tasks.</p>}
        {insights?.overdue.slice(0, 5).map((t) => (
          <p key={t.id} className="flex items-start gap-2">
            <Clock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" />
            <span>
              <strong>{t.task}</strong> ({t.owner}) is {t.daysOverdue}d overdue · {t.meetingTitle}
            </span>
          </p>
        ))}
        {insights?.duplicates.map((p) => (
          <p key={p.a.id + p.b.id} className="flex items-start gap-2">
            <Copy className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span>
              Duplicate: “{p.a.task}” in {p.a.meetingTitle} and {p.b.meetingTitle}
            </span>
          </p>
        ))}
        {insights?.conflicts.map((p) => (
          <p key={p.a.id + p.b.id} className="flex items-start gap-2">
            <GitCompare className="mt-0.5 h-3.5 w-3.5 shrink-0 text-priority-medium" />
            <span>
              Conflict ({p.reason}): “{p.a.task}” — {p.a.owner} vs {p.b.owner}
            </span>
          </p>
        ))}
      </CardContent>
    </Card>
  );
}
