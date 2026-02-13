"use client";

import type { ResearchState, ClarificationAnswer } from "@/lib/types";
import { PromptInput } from "./PromptInput";
import { ProgressSteps } from "./ProgressSteps";
import { ClarificationPanel } from "./ClarificationPanel";

interface SidebarProps {
  researchState: ResearchState;
  onSubmitPrompt: (prompt: string) => void;
  onSubmitClarification: (answers: ClarificationAnswer[]) => void;
  onSelectCompetitors: (ids: string[]) => void;
  onSelectProblems: (ids: string[]) => void;
}

export function Sidebar({
  researchState,
  onSubmitPrompt,
  onSubmitClarification,
}: SidebarProps) {
  const {
    phase,
    intentType,
    currentStep,
    completedSteps,
    clarificationQuestions,
    quickResponse,
  } = researchState;

  const waitingForSelection =
    phase === "waiting_for_competitors" || phase === "waiting_for_problems";

  const isStreaming = phase === "streaming";

  return (
    <aside className="flex h-full flex-col bg-sand p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-charcoal">
          <span className="font-sans text-sm font-bold text-workspace">B</span>
        </div>
        <span className="font-sans text-lg font-semibold text-charcoal">Blueprint</span>
      </div>

      {/* Progress */}
      <div className="mb-6 shrink-0 rounded-panel bg-workspace p-4">
        <ProgressSteps
          intentType={intentType}
          currentStep={currentStep}
          completedSteps={completedSteps}
          waitingForSelection={waitingForSelection}
        />

        {/* Streaming loader — visible while backend is working */}
        {isStreaming && (
          <div className="mt-4 flex items-center gap-3">
            <div className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-terracotta [animation-delay:0ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-terracotta [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-terracotta [animation-delay:300ms]" />
            </div>
            <span className="font-sans text-[13px] text-secondary">
              Researching...
            </span>
          </div>
        )}
      </div>

      {/* Scrollable interaction area */}
      <div className="flex min-h-0 flex-1 flex-col rounded-panel bg-workspace">
        <div className="flex-1 overflow-y-auto p-4">
          {quickResponse && (
            <div className="mb-4 rounded-card border border-border bg-sand p-4">
              <p className="font-sans text-[14px] text-charcoal">{quickResponse}</p>
            </div>
          )}

          {phase === "waiting_for_clarification" && clarificationQuestions && (
            <ClarificationPanel
              questions={clarificationQuestions}
              onSubmit={onSubmitClarification}
              disabled={false}
            />
          )}

          {phase === "waiting_for_competitors" && (
            <p className="font-sans text-[14px] font-medium text-charcoal">
              Select competitors to explore
            </p>
          )}

          {phase === "waiting_for_problems" && (
            <p className="font-sans text-[14px] font-medium text-charcoal">
              Select problem areas
            </p>
          )}

          {phase === "idle" && !quickResponse && (
            <p className="font-sans text-[14px] text-secondary">
              What would you like to build or explore? Describe your idea below.
            </p>
          )}

          {phase === "completed" && researchState.summary && (
            <p className="font-sans text-[14px] text-secondary">{researchState.summary}</p>
          )}
        </div>

        {/* Prompt input — pinned at bottom, never scrolls away */}
        <div className="shrink-0 border-t border-border p-3">
          <PromptInput
            onSubmit={onSubmitPrompt}
            disabled={isStreaming}
            placeholder="Describe what you want to build or explore..."
            compact
          />
        </div>
      </div>
    </aside>
  );
}
