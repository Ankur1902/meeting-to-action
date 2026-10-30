"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, Check, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, approveAction, listActions, proposeActions, rejectAction } from "@/services/api";
import type { AgentAction } from "@/types/agent";

interface AgentPanelProps {
  meetingId: string | null;
}

/**
 * Human-in-the-loop agent actions: the agent drafts a follow-up email and
 * GitHub issues; nothing runs until a person clicks Approve.
 */
export function AgentPanel({ meetingId }: AgentPanelProps) {
  const [actions, setActions] = useState<AgentAction[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setActions(await listActions());
    } catch {
      /* backend offline — leave the list as is */
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh, meetingId]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setBusy(false);
    }
  }

  if (!meetingId && actions.length === 0) return null;

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-accent" />
          <CardTitle className="text-base">Agent actions (need your approval)</CardTitle>
        </div>
        {meetingId && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => run(() => proposeActions(meetingId))}>
            Draft follow-ups
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <p className="text-sm text-destructive">{error}</p>}
        {actions.length === 0 && <p className="text-sm text-muted-foreground">No proposals yet.</p>}
        {actions.map((a) => (
          <div key={a.id} className="space-y-2 rounded-md border border-border p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">
                {a.kind === "email_draft" ? `Email: ${a.payload.subject}` : `GitHub issue: ${a.payload.title}`}
              </span>
              <Badge variant="outline">{a.status}</Badge>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-xs text-muted-foreground">{a.payload.body}</pre>
            {a.status === "pending" && (
              <div className="flex gap-2">
                <Button size="sm" disabled={busy} onClick={() => run(() => approveAction(a.id))}>
                  <Check /> Approve
                </Button>
                <Button size="sm" variant="ghost" disabled={busy} onClick={() => run(() => rejectAction(a.id))}>
                  <X /> Reject
                </Button>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
