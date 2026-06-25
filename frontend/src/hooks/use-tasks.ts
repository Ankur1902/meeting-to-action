"use client";

import { useCallback } from "react";

import { useLocalStorageState } from "@/hooks/use-local-storage";
import { STORAGE_KEYS } from "@/lib/storage";
import type { Task, TaskStatus } from "@/types/task";

interface UseTasksResult {
  tasks: Task[];
  hydrated: boolean;
  addTasks: (newTasks: Task[]) => void;
  moveTask: (taskId: string, status: TaskStatus) => void;
  removeTask: (taskId: string) => void;
  clearTasks: () => void;
  stats: {
    total: number;
    open: number;
    completed: number;
    highPriority: number;
  };
}

/**
 * Single source of truth for the task list. Backed by LocalStorage so the
 * board survives a refresh. Exposes the small set of mutations the rest
 * of the app needs (append from AI extraction, move between Kanban
 * columns, remove, clear) rather than a raw setState, so every write
 * path stays consistent.
 */
export function useTasks(): UseTasksResult {
  const [tasks, setTasks, hydrated] = useLocalStorageState<Task[]>(STORAGE_KEYS.tasks, []);

  const addTasks = useCallback(
    (newTasks: Task[]) => {
      setTasks((prev) => [...prev, ...newTasks]);
    },
    [setTasks]
  );

  const moveTask = useCallback(
    (taskId: string, status: TaskStatus) => {
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status } : t))
      );
    },
    [setTasks]
  );

  const removeTask = useCallback(
    (taskId: string) => {
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    },
    [setTasks]
  );

  const clearTasks = useCallback(() => {
    setTasks([]);
  }, [setTasks]);

  const stats = {
    total: tasks.length,
    open: tasks.filter((t) => t.status !== "done").length,
    completed: tasks.filter((t) => t.status === "done").length,
    highPriority: tasks.filter((t) => t.priority === "High").length,
  };

  return { tasks, hydrated, addTasks, moveTask, removeTask, clearTasks, stats };
}
