import type { Task } from "@/types/task";

export interface MeetingSummary {
  executiveSummary: string;
  keyDecisions: string[];
}

/** Shape returned by both POST /api/extract and /api/extract/upload */
export interface ExtractResponse {
  summary: MeetingSummary;
  tasks: Task[];
}
