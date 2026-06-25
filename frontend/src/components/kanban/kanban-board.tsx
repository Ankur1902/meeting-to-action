"use client";

import { useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";

import { KanbanColumn } from "@/components/kanban/kanban-column";
import { TaskCard } from "@/components/kanban/task-card";
import type { Task, TaskStatus } from "@/types/task";
import { PRIORITY_ORDER } from "@/types/task";

const COLUMN_ORDER: TaskStatus[] = ["todo", "in_progress", "done"];

function isTaskStatus(value: unknown): value is TaskStatus {
  return value === "todo" || value === "in_progress" || value === "done";
}

interface KanbanBoardProps {
  tasks: Task[];
  onMoveTask: (taskId: string, status: TaskStatus) => void;
  onRemoveTask: (taskId: string) => void;
}

export function KanbanBoard({ tasks, onMoveTask, onRemoveTask }: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  // A short drag distance threshold on the pointer sensor lets the click
  // handler on the remove (X) button still fire normally — without it,
  // dnd-kit can swallow plain clicks as the start of a drag.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor)
  );

  const columns = useMemo(() => {
    const grouped: Record<TaskStatus, Task[]> = { todo: [], in_progress: [], done: [] };
    for (const task of tasks) {
      grouped[task.status].push(task);
    }
    for (const status of COLUMN_ORDER) {
      grouped[status].sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]);
    }
    return grouped;
  }, [tasks]);

  function handleDragStart(event: DragStartEvent) {
    const task = tasks.find((t) => t.id === event.active.id);
    setActiveTask(task ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;
    const newStatus = over.id;
    if (!isTaskStatus(newStatus)) return;

    const task = tasks.find((t) => t.id === active.id);
    if (!task || task.status === newStatus) return;

    onMoveTask(task.id, newStatus);
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragCancel={() => setActiveTask(null)}
    >
      <div className="grid gap-4 sm:grid-cols-3">
        {COLUMN_ORDER.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            tasks={columns[status]}
            onRemoveTask={onRemoveTask}
          />
        ))}
      </div>

      <DragOverlay>
        {activeTask ? <TaskCard task={activeTask} isOverlay /> : null}
      </DragOverlay>
    </DndContext>
  );
}
