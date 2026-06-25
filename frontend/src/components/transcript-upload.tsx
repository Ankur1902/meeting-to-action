"use client";

import { useRef, useState } from "react";
import { FileText, Upload, X, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [".txt", ".pdf"];
const ACCEPTED_INPUT_ATTR = ACCEPTED_EXTENSIONS.join(",");

interface TranscriptUploadProps {
  onGenerate: (file: File) => void;
  isLoading: boolean;
}

function isAcceptedFile(file: File): boolean {
  const lowerName = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
}

export function TranscriptUpload({ onGenerate, isLoading }: TranscriptUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(fileList: FileList | null) {
    const candidate = fileList?.[0];
    if (!candidate) return;

    if (!isAcceptedFile(candidate)) {
      setValidationError("Only .txt and .pdf files are supported.");
      setFile(null);
      return;
    }

    setValidationError(null);
    setFile(candidate);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }

  function handleClear() {
    setFile(null);
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <Card className="flex h-full flex-col">
      <CardHeader>
        <CardTitle>Upload a transcript</CardTitle>
        <CardDescription>TXT or PDF — we&apos;ll extract the text automatically.</CardDescription>
      </CardHeader>
      <CardContent className="flex-1">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          className={cn(
            "flex h-full min-h-[220px] cursor-pointer flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed border-border px-4 text-center transition-colors",
            dragActive && "border-accent bg-accent/5",
            file && "border-secondary bg-secondary/5"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_INPUT_ATTR}
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
            disabled={isLoading}
          />

          {file ? (
            <>
              <FileText className="h-8 w-8 text-secondary" />
              <div className="flex items-center gap-2">
                <span className="max-w-[220px] truncate text-sm font-medium">{file.name}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleClear();
                  }}
                  aria-label="Remove file"
                  className="text-muted-foreground hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <span className="text-xs text-muted-foreground">
                {(file.size / 1024).toFixed(0)} KB
              </span>
            </>
          ) : (
            <>
              <Upload className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Drag and drop, or <span className="text-accent underline">browse</span>
              </p>
              <p className="text-xs text-muted-foreground">Supports .txt and .pdf</p>
            </>
          )}
        </div>
        {validationError && (
          <p className="mt-2 text-xs text-destructive">{validationError}</p>
        )}
      </CardContent>
      <CardFooter className="justify-end">
        <Button onClick={() => file && onGenerate(file)} disabled={!file || isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating&hellip;
            </>
          ) : (
            "Generate tasks"
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
