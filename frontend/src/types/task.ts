export type Priority = "High" | "Medium" | "Low";

export type TaskStatus = "todo" | "in_progress" | "done";

export interface Evidence {
  quote: string;
  start: number;
  end: number;
  score: number;
  verified: boolean;
}

export interface Task {
  id: string;
  task: string;
  owner: string;
  deadline: string;
  priority: Priority;
  status: TaskStatus;
  dueDate?: string | null;
  /** Transcript quote this task was derived from. */
  evidence?: Evidence | null;
  /** False when the quote/owner could not be verified against the transcript. */
  supported?: boolean;
  confidence?: number;
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "Todo",
  in_progress: "In Progress",
  done: "Done",
};

export const PRIORITY_ORDER: Record<Priority, number> = {
  High: 0,
  Medium: 1,
  Low: 2,
};
