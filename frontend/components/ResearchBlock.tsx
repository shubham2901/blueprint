"use client";

import { useState } from "react";
import type { ResearchBlock as ResearchBlockType, RefineRequest } from "@/lib/types";

// Map block type to refine step type
const BLOCK_TO_REFINE_STEP: Record<string, RefineRequest["step_type"] | null> = {
  competitor_list: "find_competitors",
  product_profile: "explore",
  gap_analysis: "gap_analysis",
  problem_statement: "define_problem",
  market_overview: null, // Not refinable
};

interface ResearchBlockProps {
  block: ResearchBlockType;
  onRefine?: (stepType: RefineRequest["step_type"], feedback?: string) => void;
  isRefining?: boolean;
}

export function ResearchBlock({ block, onRefine, isRefining = false }: ResearchBlockProps) {
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);
  const [feedback, setFeedback] = useState("");

  const refineStepType = BLOCK_TO_REFINE_STEP[block.type];
  const canRefine = refineStepType !== null && onRefine !== undefined;

  const handleRefineClick = () => {
    if (!canRefine || !refineStepType) return;
    
    if (showFeedbackInput && feedback.trim()) {
      // Submit with feedback
      onRefine(refineStepType, feedback.trim());
      setShowFeedbackInput(false);
      setFeedback("");
    } else if (showFeedbackInput) {
      // Submit without feedback
      onRefine(refineStepType);
      setShowFeedbackInput(false);
    } else {
      // Show feedback input first
      setShowFeedbackInput(true);
    }
  };

  const handleQuickRefine = () => {
    if (!canRefine || !refineStepType) return;
    onRefine(refineStepType);
    setShowFeedbackInput(false);
    setFeedback("");
  };

  return (
    <article
      className="rounded-card border border-border bg-workspace p-5 shadow-subtle"
      data-block-id={block.id}
      data-block-type={block.type}
    >
      <header className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-sans text-base font-semibold text-charcoal">{block.title}</h3>
          {block.cached && (
            <span className="rounded-chip border border-border bg-sand px-2 py-0.5 font-sans text-[11px] text-secondary">
              Cached
            </span>
          )}
        </div>
        {canRefine && (
          <button
            onClick={handleQuickRefine}
            disabled={isRefining}
            className="flex items-center gap-1 rounded-button border border-border bg-workspace px-3 py-1.5 font-sans text-[12px] font-medium text-secondary transition-colors hover:bg-sand hover:text-charcoal disabled:opacity-50"
            title="Refine this section for more/better results"
          >
            {isRefining ? (
              <>
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-terracotta border-t-transparent" />
                Refining...
              </>
            ) : (
              <>
                <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refine
              </>
            )}
          </button>
        )}
      </header>
      <div className="font-sans text-[14px] leading-relaxed text-charcoal whitespace-pre-wrap">
        {block.content}
      </div>
      
      {/* Feedback input for refinement */}
      {showFeedbackInput && (
        <div className="mt-4 flex gap-2">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What would you like to improve? (optional)"
            className="flex-1 rounded-card border border-border bg-workspace px-3 py-2 font-sans text-[13px] text-charcoal placeholder:text-placeholder focus:border-terracotta focus:outline-none"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleRefineClick();
              if (e.key === "Escape") setShowFeedbackInput(false);
            }}
          />
          <button
            onClick={handleRefineClick}
            className="rounded-button bg-terracotta px-4 py-2 font-sans text-[12px] font-medium text-workspace transition-opacity hover:opacity-90"
          >
            Go
          </button>
          <button
            onClick={() => setShowFeedbackInput(false)}
            className="rounded-button border border-border px-3 py-2 font-sans text-[12px] font-medium text-secondary transition-colors hover:bg-sand"
          >
            Cancel
          </button>
        </div>
      )}
      
      {block.sources && block.sources.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {block.sources.map((url, i) => (
            <a
              key={i}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-sans text-[12px] text-terracotta underline hover:no-underline"
            >
              Source {i + 1}
            </a>
          ))}
        </div>
      )}
    </article>
  );
}
