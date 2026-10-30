"use client";

import { useDraggable } from "@dnd-kit/core";
import { useState } from "react";
import { AlertTriangle, GripVertical, Quote, X } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Task } from "@/types/task";

const PRIORITY_TAB_CLASS: Record<Task["priority"], string> = {
  High: "border-priority-high",
  Medium: "border-priority-medium",
  Low: "border-priority-low",
};

const PRIORITY_TEXT_CLASS: Record<Task["priority"], string> = {
  High: "text-priority-high",
  Medium: "text-priority-medium",
  Low: "text-priority-low",
};

interface TaskCardProps {
  task: Task;
  onRemove?: (id: string) => void;
  /** Rendered inside DragOverlay — static, no drag listeners of its own. */
  isOverlay?: boolean;
}

function initials(name: string): string {
  const trimmed = name.trim();
  if (!trimmed) return "?";
  return trimmed
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function TaskCard({ task, onRemove, isOverlay = false }: TaskCardProps) {
  const [showEvidence, setShowEvidence] = useState(false);
  const unverified = task.supported === false;
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: task.id,
    disabled: isOverlay,
  });

  return (
    <div
      ref={isOverlay ? undefined : setNodeRef}
      className={cn(
        "group relative flex flex-col gap-2 rounded-md border-l-4 border-border bg-card p-3 text-sm shadow-sm transition-shadow",
        PRIORITY_TAB_CLASS[task.priority],
        isDragging && "opacity-40",
        isOverlay && "rotate-1 shadow-lg"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="leading-snug">{task.task}</p>
        <div className="flex shrink-0 items-center gap-0.5">
          {onRemove && (
            <button
              type="button"
              aria-label="Remove task"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={() => onRemove(task.id)}
              className="rounded p-0.5 text-muted-foreground opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          {!isOverlay && (
            <button
              type="button"
              aria-label="Drag task"
              {...attributes}
              {...listeners}
              className="cursor-grab touch-none rounded p-0.5 text-muted-foreground opacity-0 transition-opacity active:cursor-grabbing group-hover:opacity-100"
            >
              <GripVertical className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-foreground">
            {initials(task.owner)}
          </span>
          <span className="truncate">{task.owner}</span>
        </div>
        <span className={cn("font-mono text-xs font-medium", PRIORITY_TEXT_CLASS[task.priority])}>
          {task.priority}
        </span>
      </div>

      <p className="font-mono text-xs text-muted-foreground">&rarr; {task.deadline}</p>

      {unverified && (
        <p className="flex items-center gap-1 text-xs text-destructive">
          <AlertTriangle className="h-3 w-3" /> Unverified — check the transcript
        </p>
      )}

      {task.evidence?.quote && (
        <div className="text-xs">
          <button
            type="button"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setShowEvidence((v) => !v)}
            className="flex items-center gap-1 text-muted-foreground hover:text-foreground"
            aria-expanded={showEvidence}
          >
            <Quote className="h-3 w-3" /> {showEvidence ? "Hide source" : "Show source"}
          </button>
          {showEvidence && (
            <blockquote className="mt-1 border-l-2 border-border pl-2 italic text-muted-foreground">
              {task.evidence.quote}
            </blockquote>
          )}
        </div>
      )}
    </div>
  );
}
