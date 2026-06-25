"use client";

import { useEffect, useState } from "react";

/**
 * Generic hook for state synced to LocalStorage under `key`. Hydrates
 * from `initialValue` on the server/first render (SSR-safe), then reads
 * the real stored value once mounted in the browser, avoiding hydration
 * mismatches between server and client render.
 */
export function useLocalStorageState<T>(
  key: string,
  initialValue: T,
  serialize: (value: T) => string = JSON.stringify,
  deserialize: (raw: string) => T = JSON.parse
): [T, React.Dispatch<React.SetStateAction<T>>, boolean] {
  const [value, setValue] = useState<T>(initialValue);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw !== null) {
        setValue(deserialize(raw));
      }
    } catch {
      // Ignore malformed/unavailable storage — fall back to initialValue.
    } finally {
      setHydrated(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(key, serialize(value));
    } catch {
      // Storage full/unavailable — no-op rather than crash.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, value, hydrated]);

  return [value, setValue, hydrated];
}
