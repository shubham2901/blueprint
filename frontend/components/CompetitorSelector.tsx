"use client";

import type { CompetitorInfo } from "@/lib/types";

interface CompetitorSelectorProps {
  competitors: CompetitorInfo[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onExplore: (ids: string[]) => void;
  disabled?: boolean;
}

export function CompetitorSelector({
  competitors,
  selectedIds,
  onSelectionChange,
  onExplore,
  disabled = false,
}: CompetitorSelectorProps) {
  const toggle = (id: string) => {
    if (disabled) return;
    const next = selectedIds.includes(id)
      ? selectedIds.filter((x) => x !== id)
      : [...selectedIds, id];
    onSelectionChange(next);
  };

  const handleExplore = () => {
    if (selectedIds.length > 0 && !disabled) {
      onExplore(selectedIds);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="font-sans text-[13px] text-secondary">
        {selectedIds.length} of {competitors.length} selected
      </p>

      <div className="flex flex-col gap-3">
        {competitors.map((c) => (
          <label
            key={c.id}
            className={`flex cursor-pointer items-start gap-3 rounded-card border border-border bg-workspace p-4 transition-colors ${
              disabled ? "cursor-not-allowed opacity-60" : "hover:border-terracotta/30"
            }`}
          >
            <input
              type="checkbox"
              checked={selectedIds.includes(c.id)}
              onChange={() => toggle(c.id)}
              disabled={disabled}
              className="mt-1 h-4 w-4 shrink-0 rounded border-border text-terracotta focus:ring-terracotta"
            />
            <div className="min-w-0 flex-1">
              <p className="font-sans text-[14px] font-semibold text-charcoal">{c.name}</p>
              <p className="mt-0.5 font-sans text-[13px] text-secondary">{c.description}</p>
              {c.pricing_model && (
                <span className="mt-1 inline-block rounded-chip border border-border bg-sand px-2 py-0.5 font-sans text-[12px] text-secondary">
                  {c.pricing_model}
                </span>
              )}
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={handleExplore}
        disabled={selectedIds.length === 0 || disabled}
        className="w-fit rounded-button bg-terracotta px-4 py-2 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        Explore Selected ({selectedIds.length})
      </button>
    </div>
  );
}
