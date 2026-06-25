"use client";

import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

interface HeaderProps {
  onClearBoard: () => void;
  hasContent: boolean;
}

export function Header({ onClearBoard, hasContent }: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <div className="flex items-baseline gap-2">
          <h1 className="font-display text-2xl italic tracking-tight">
            Minutes <span className="text-accent">&rarr;</span> Action
          </h1>
          <span className="hidden text-xs text-muted-foreground sm:inline">
            meeting notes, turned into work
          </span>
        </div>

        <div className="flex items-center gap-1">
          {hasContent && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearBoard}
              className="text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="h-4 w-4" />
              <span className="hidden sm:inline">Clear board</span>
            </Button>
          )}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
