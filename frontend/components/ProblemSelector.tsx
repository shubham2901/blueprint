"use client";

import type { ProblemArea } from "@/lib/types";

interface ProblemSelectorProps {
  problems: ProblemArea[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  onDefine: (ids: string[]) => void;
  disabled?: boolean;
}

const SIZE_BADGE_CLASSES: Record<string, string> = {
  high: "bg-terracotta-light border-terracotta text-terracotta",
  medium: "bg-sand border-secondary text-secondary",
  low: "bg-sand border-placeholder text-placeholder",
};

function getBadgeClass(size?: string) {
  const lower = size?.toLowerCase() ?? "low";
  return SIZE_BADGE_CLASSES[lower] ?? SIZE_BADGE_CLASSES.low;
}

export function ProblemSelector({
  problems,
  selectedIds,
  onSelectionChange,
  onDefine,
  disabled = false,
}: ProblemSelectorProps) {
  const toggle = (id: string) => {
    if (disabled) return;
    const next = selectedIds.includes(id)
      ? selectedIds.filter((x) => x !== id)
      : [...selectedIds, id];
    onSelectionChange(next);
  };

  const handleDefine = () => {
    if (selectedIds.length > 0 && !disabled) {
      onDefine(selectedIds);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <p className="font-sans text-[13px] text-secondary">
        {selectedIds.length} of {problems.length} selected
      </p>

      <div className="flex flex-col gap-3">
        {problems.map((p) => (
          <label
            key={p.id}
            className={`flex cursor-pointer items-start gap-3 rounded-card border border-border bg-workspace p-4 transition-colors ${
              disabled ? "cursor-not-allowed opacity-60" : "hover:border-terracotta/30"
            }`}
          >
            <input
              type="checkbox"
              checked={selectedIds.includes(p.id)}
              onChange={() => toggle(p.id)}
              disabled={disabled}
              className="mt-1 h-4 w-4 shrink-0 rounded border-border text-terracotta focus:ring-terracotta"
            />
            <div className="min-w-0 flex-1">
              <p className="font-sans text-[14px] font-semibold text-charcoal">{p.title}</p>
              <p className="mt-0.5 font-sans text-[13px] text-secondary">{p.description}</p>
              {p.evidence && p.evidence.length > 0 && (
                <ul className="mt-2 list-inside list-disc space-y-1 font-sans text-[12px] text-secondary">
                  {p.evidence.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
              {p.opportunity_size && (
                <span
                  className={`mt-2 inline-block rounded-chip border px-2 py-0.5 font-sans text-[12px] capitalize ${getBadgeClass(
                    p.opportunity_size
                  )}`}
                >
                  {p.opportunity_size}
                </span>
              )}
            </div>
          </label>
        ))}
      </div>

      <button
        onClick={handleDefine}
        disabled={selectedIds.length === 0 || disabled}
        className="w-fit rounded-button bg-terracotta px-4 py-2 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        Define Problem ({selectedIds.length})
      </button>
    </div>
  );
}
