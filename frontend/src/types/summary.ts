import type { Task } from "@/types/task";

export interface MeetingSummary {
  executiveSummary: string;
  keyDecisions: string[];
}

export interface TraceStep {
  step: string;
  durationMs: number;
  detail: string;
}

/** Shape returned by both POST /api/extract and /api/extract/upload */
export interface ExtractResponse {
  summary: MeetingSummary;
  tasks: Task[];
  meetingId?: string | null;
  warnings?: string[];
  trace?: TraceStep[];
}
