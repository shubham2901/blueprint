"use client";

import { useCallback, useRef } from "react";

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  disabled?: boolean;
  placeholder?: string;
  compact?: boolean;
}

export function PromptInput({
  onSubmit,
  disabled = false,
  placeholder = "Describe what you want to build or explore...",
  compact = false,
}: PromptInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = useCallback(() => {
    const value = textareaRef.current?.value?.trim();
    if (value && !disabled) {
      onSubmit(value);
      if (textareaRef.current) textareaRef.current.value = "";
    }
  }, [onSubmit, disabled]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      className={`relative w-full rounded-input border border-border bg-workspace shadow-subtle ${
        compact ? "p-2" : "p-4"
      }`}
    >
      <textarea
        ref={textareaRef}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={compact ? 2 : 3}
        className={`w-full resize-none rounded-input bg-transparent font-sans text-[15px] text-charcoal placeholder:text-placeholder focus:outline-none disabled:opacity-50 ${
          compact ? "px-2 pt-2 pb-10" : "px-4 pt-4 pb-12"
        }`}
      />
      <div className={`absolute right-3 ${compact ? "bottom-2" : "bottom-3"}`}>
        <button
          onClick={handleSubmit}
          disabled={disabled}
          className="rounded-button bg-charcoal px-4 py-1.5 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          {disabled ? "Researching..." : "RUN"}
        </button>
      </div>
    </div>
  );
}
