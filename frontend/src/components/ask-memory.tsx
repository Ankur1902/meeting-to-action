"use client";

import { useState } from "react";
import { Brain, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { askMemory, ApiError } from "@/services/api";
import type { AskResponse } from "@/types/agent";

/** Cited Q&A over every meeting stored in the backend's memory. */
export function AskMemory() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskResponse | null>(null);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (question.trim().length < 3) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await askMemory(question.trim()));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reach the memory service.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <Brain className="h-4 w-4 text-accent" />
        <CardTitle className="text-base">Ask your meetings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <form onSubmit={handleAsk} className="flex gap-2">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What did we decide about pricing last month?"
            aria-label="Question about past meetings"
          />
          <Button type="submit" disabled={loading || question.trim().length < 3}>
            {loading ? <Loader2 className="animate-spin" /> : "Ask"}
          </Button>
        </form>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {result && (
          <div className="space-y-2 text-sm">
            <p className="leading-relaxed">{result.answer}</p>
            <ol className="space-y-1 text-xs text-muted-foreground">
              {result.sources.map((s) => (
                <li key={s.id}>
                  <span className="font-mono">[{s.id}]</span> {s.meetingTitle} · {s.meetingDate} —{" "}
                  <span className="italic">{s.text.slice(0, 140)}</span>
                </li>
              ))}
            </ol>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
