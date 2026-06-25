"use client";

import { useCallback, useState } from "react";

import { extractFromText, extractFromUpload, ApiError } from "@/services/api";
import type { ExtractResponse } from "@/types/summary";

interface UseExtractResult {
  isLoading: boolean;
  error: string | null;
  runExtractFromText: (text: string) => Promise<ExtractResponse | null>;
  runExtractFromUpload: (file: File) => Promise<ExtractResponse | null>;
  clearError: () => void;
}

/**
 * Wraps both extraction API calls (pasted text + file upload) behind a
 * single loading/error state so the UI components that trigger them
 * (notes input, transcript upload) don't each reimplement try/catch and
 * spinner logic.
 */
export function useExtract(): UseExtractResult {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = useCallback(
    async (fn: () => Promise<ExtractResponse>): Promise<ExtractResponse | null> => {
      setIsLoading(true);
      setError(null);
      try {
        return await fn();
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError("Something went wrong while contacting the AI service. Please try again.");
        }
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const runExtractFromText = useCallback(
    (text: string) => handle(() => extractFromText(text)),
    [handle]
  );

  const runExtractFromUpload = useCallback(
    (file: File) => handle(() => extractFromUpload(file)),
    [handle]
  );

  const clearError = useCallback(() => setError(null), []);

  return { isLoading, error, runExtractFromText, runExtractFromUpload, clearError };
}
