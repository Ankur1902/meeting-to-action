"use client";

import { useState } from "react";

import { Header } from "@/components/header";
import { MeetingNotesInput } from "@/components/meeting-notes-input";
import { TranscriptUpload } from "@/components/transcript-upload";
import { SummaryCards } from "@/components/summary-cards";
import { StatsDashboard } from "@/components/stats-dashboard";
import { EmptyState } from "@/components/empty-state";
import { AgentPanel } from "@/components/agent-panel";
import { AskMemory } from "@/components/ask-memory";
import { InsightsPanel } from "@/components/insights-panel";
import { KanbanBoard } from "@/components/kanban/kanban-board";
import { Separator } from "@/components/ui/separator";
import { useTasks } from "@/hooks/use-tasks";
import { useExtract } from "@/hooks/use-extract";
import { useLocalStorageState } from "@/hooks/use-local-storage";
import { STORAGE_KEYS } from "@/lib/storage";
import type { ExtractResponse, MeetingSummary } from "@/types/summary";

export default function Home() {
  const { tasks, hydrated, addTasks, moveTask, removeTask, clearTasks, stats } = useTasks();
  const [summary, setSummary] = useLocalStorageState<MeetingSummary | null>(
    STORAGE_KEYS.summary,
    null
  );
  const { isLoading, error, runExtractFromText, runExtractFromUpload, clearError } =
    useExtract();
  const [activeError, setActiveError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [meetingId, setMeetingId] = useState<string | null>(null);

  async function handleGenerateFromText(text: string) {
    clearError();
    const result = await runExtractFromText(text);
    if (result) applyResult(result);
  }

  async function handleGenerateFromUpload(file: File) {
    clearError();
    const result = await runExtractFromUpload(file);
    if (result) applyResult(result);
  }

  function applyResult(result: ExtractResponse) {
    setWarnings(result.warnings ?? []);
    setMeetingId(result.meetingId ?? null);
    setSummary(result.summary);
    addTasks(result.tasks);
  }

  function handleClearBoard() {
    clearTasks();
    setSummary(null);
    setWarnings([]);
    setMeetingId(null);
  }

  const displayError = error ?? activeError;

  return (
    <div className="min-h-screen bg-background">
      <Header onClearBoard={handleClearBoard} hasContent={tasks.length > 0 || !!summary} />

      <main className="mx-auto flex max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6">
        {displayError && (
          <div
            role="alert"
            className="flex items-center justify-between rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
          >
            <span>{displayError}</span>
            <button
              onClick={() => {
                clearError();
                setActiveError(null);
              }}
              className="font-medium underline"
            >
              Dismiss
            </button>
          </div>
        )}

        <section className="grid gap-4 lg:grid-cols-2">
          <MeetingNotesInput onGenerate={handleGenerateFromText} isLoading={isLoading} />
          <TranscriptUpload onGenerate={handleGenerateFromUpload} isLoading={isLoading} />
        </section>

        {warnings.length > 0 && (
          <div
            role="status"
            className="rounded-md border border-priority-medium/40 bg-priority-medium/10 px-4 py-3 text-sm"
          >
            <ul className="list-disc space-y-1 pl-4">
              {warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {summary && (
          <section>
            <SummaryCards summary={summary} />
          </section>
        )}

        {hydrated && tasks.length > 0 && (
          <section>
            <StatsDashboard stats={stats} />
          </section>
        )}

        <Separator />

        <section className="grid gap-4 lg:grid-cols-2">
          <AskMemory />
          <InsightsPanel refreshKey={meetingId} />
        </section>

        <AgentPanel meetingId={meetingId} />

        <Separator />

        <section className="flex flex-col gap-4">
          <h2 className="font-display text-xl">Board</h2>

          {!hydrated ? null : tasks.length === 0 ? (
            <EmptyState />
          ) : (
            <KanbanBoard tasks={tasks} onMoveTask={moveTask} onRemoveTask={removeTask} />
          )}
        </section>
      </main>
    </div>
  );
}
