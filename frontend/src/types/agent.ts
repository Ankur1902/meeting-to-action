import type { Task } from "@/types/task";

export interface MemorySource {
  id: number;
  meetingId: string;
  meetingTitle: string;
  meetingDate: string;
  text: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  sources: MemorySource[];
}

export interface MemoryTask extends Task {
  meetingId: string;
  meetingTitle: string;
  meetingDate: string;
  daysOverdue?: number;
}

export interface TaskPair {
  a: MemoryTask;
  b: MemoryTask;
  similarity: number;
  reason?: string;
}

export interface Insights {
  overdue: MemoryTask[];
  duplicates: TaskPair[];
  conflicts: TaskPair[];
}

export type ActionStatus = "pending" | "executed" | "rejected" | "failed";

export interface AgentAction {
  id: string;
  meetingId: string | null;
  kind: "email_draft" | "github_issue";
  status: ActionStatus;
  payload: { subject?: string; body: string; title?: string };
  result: Record<string, unknown> | null;
}
