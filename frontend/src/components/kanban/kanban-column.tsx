"use client";

import { useDroppable } from "@dnd-kit/core";

import { Badge } from "@/components/ui/badge";
import { TaskCard } from "@/components/kanban/task-card";
import { cn } from "@/lib/utils";
import type { Task, TaskStatus } from "@/types/task";
import { STATUS_LABELS } from "@/types/task";

interface KanbanColumnProps {
  status: TaskStatus;
  tasks: Task[];
  onRemoveTask: (id: string) => void;
}

export function KanbanColumn({ status, tasks, onRemoveTask }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-medium text-muted-foreground">
          {STATUS_LABELS[status]}
        </h3>
        <Badge variant="muted">{tasks.length}</Badge>
      </div>

      <div
        ref={setNodeRef}
        className={cn(
          "flex min-h-[120px] flex-1 flex-col gap-2 rounded-lg border border-dashed border-transparent p-2 transition-colors",
          isOver && "border-accent bg-accent/5"
        )}
      >
        {tasks.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-muted-foreground">
            Drop a task here
          </p>
        )}
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onRemove={onRemoveTask} />
        ))}
      </div>
    </div>
  );
}
