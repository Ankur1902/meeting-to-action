"use client";

import { useState } from "react";
import { Sparkles, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

const PLACEHOLDER = `John will prepare the Q3 sales report by Friday.
Sarah needs to review the dashboard redesign by July 10.
Mike should update API documentation before launch.`;

interface MeetingNotesInputProps {
  onGenerate: (text: string) => void;
  isLoading: boolean;
}

export function MeetingNotesInput({ onGenerate, isLoading }: MeetingNotesInputProps) {
  const [notes, setNotes] = useState("");

  const canGenerate = notes.trim().length > 0 && !isLoading;

  function handleSubmit() {
    if (!canGenerate) return;
    onGenerate(notes.trim());
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Paste meeting notes</CardTitle>
        <CardDescription>
          Drop in raw notes from the meeting. We&apos;ll summarize them and pull out
          every action item.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder={PLACEHOLDER}
          rows={10}
          className="h-full min-h-[220px] resize-none font-sans text-sm"
          disabled={isLoading}
          aria-label="Meeting notes"
        />
      </CardContent>
      <CardFooter className="justify-end">
        <Button onClick={handleSubmit} disabled={!canGenerate}>
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating&hellip;
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate tasks
            </>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
