import type { AgentAction, AskResponse, Insights } from "@/types/agent";
import type { ExtractResponse } from "@/types/summary";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // response wasn't JSON — fall through to generic message
  }
  return `Request failed with status ${response.status}`;
}

/**
 * Sends pasted meeting notes to the backend for summarization and task
 * extraction.
 */
export async function extractFromText(text: string): Promise<ExtractResponse> {
  const response = await fetch(`${API_BASE_URL}/api/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorDetail(response), response.status);
  }

  return response.json() as Promise<ExtractResponse>;
}

/**
 * Uploads a TXT/PDF transcript file to the backend for summarization and
 * task extraction.
 */
export async function extractFromUpload(file: File): Promise<ExtractResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/extract/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new ApiError(await parseErrorDetail(response), response.status);
  }

  return response.json() as Promise<ExtractResponse>;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new ApiError(await parseErrorDetail(response), response.status);
  }
  return response.json() as Promise<T>;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

/** Ask a question across every stored meeting; answers carry numbered source citations. */
export function askMemory(question: string): Promise<AskResponse> {
  return request("/api/memory/ask", json({ question }));
}

/** Overdue carry-overs, duplicate and conflicting tasks across meetings. */
export function getInsights(): Promise<Insights> {
  return request("/api/memory/insights");
}

export function proposeActions(meetingId: string): Promise<AgentAction[]> {
  return request(`/api/actions/propose/${meetingId}`, { method: "POST" });
}

export function listActions(): Promise<AgentAction[]> {
  return request("/api/actions");
}

export function approveAction(id: string): Promise<AgentAction> {
  return request(`/api/actions/${id}/approve`, { method: "POST" });
}

export function rejectAction(id: string): Promise<AgentAction> {
  return request(`/api/actions/${id}/reject`, { method: "POST" });
}
