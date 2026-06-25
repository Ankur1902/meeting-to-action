/**
 * Single source of truth for every LocalStorage key the app uses.
 * Actual reads/writes happen through `useLocalStorageState` (see
 * hooks/use-local-storage.ts), which already handles SSR-safety,
 * JSON parsing, and failure modes (private browsing, quota errors).
 * Keeping the key strings here means they're defined exactly once.
 */
export const STORAGE_KEYS = {
  tasks: "meeting-board:tasks",
  summary: "meeting-board:summary",
} as const;
