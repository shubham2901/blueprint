"use client";

import type {
  ResearchBlock as ResearchBlockType,
  BlockErrorEvent,
  CompetitorInfo,
  ProblemArea,
  FatalError,
  RefineRequest,
} from "@/lib/types";
import { ResearchBlock } from "./ResearchBlock";
import { BlockErrorCard } from "./BlockErrorCard";
import { CompetitorSelector } from "./CompetitorSelector";
import { ProblemSelector } from "./ProblemSelector";

interface WorkspaceProps {
  blocks: ResearchBlockType[];
  blockErrors: BlockErrorEvent[];
  phase: string;
  fatalError: FatalError | null;
  competitorList: CompetitorInfo[] | null;
  selectedCompetitors: string[];
  onCompetitorSelectionChange: (ids: string[]) => void;
  onExploreCompetitors: (ids: string[]) => void;
  problemAreas: ProblemArea[] | null;
  selectedProblems: string[];
  onProblemSelectionChange: (ids: string[]) => void;
  onDefineProblems: (ids: string[]) => void;
  onStartNew: () => void;
  onRefine?: (stepType: RefineRequest["step_type"], feedback?: string) => void;
  isRefining?: boolean;
}

export function Workspace({
  blocks,
  blockErrors,
  phase,
  fatalError,
  competitorList,
  selectedCompetitors,
  onCompetitorSelectionChange,
  onExploreCompetitors,
  problemAreas,
  selectedProblems,
  onProblemSelectionChange,
  onDefineProblems,
  onStartNew,
  onRefine,
  isRefining = false,
}: WorkspaceProps) {
  const waitingForCompetitors = phase === "waiting_for_competitors";
  const waitingForProblems = phase === "waiting_for_problems";
  const hasError = phase === "error" && fatalError;

  return (
    <div className="flex h-full flex-col bg-workspace rounded-panel overflow-hidden">
      {/* Tab header */}
      <header className="border-b border-border px-6 py-4">
        <h2 className="font-sans text-base font-medium text-charcoal">Research</h2>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Fatal error state */}
        {hasError && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
              <svg className="h-6 w-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <p className="font-serif text-xl text-charcoal">
              {fatalError.message}
            </p>
            <p className="mt-2 font-sans text-[13px] text-placeholder">
              (Ref: {fatalError.errorCode})
            </p>
            <button
              onClick={onStartNew}
              className="mt-6 rounded-button bg-charcoal px-5 py-2 font-sans text-[14px] font-medium text-workspace transition-opacity hover:opacity-90"
            >
              Start New Research
            </button>
          </div>
        )}

        {blocks.length === 0 && !waitingForCompetitors && !waitingForProblems && phase !== "streaming" && !hasError && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="font-serif text-xl italic text-placeholder">
              Begin your inquiry.
            </p>
            <p className="mt-2 font-sans text-[14px] text-secondary">
              Your research notes and discovered insights will be collected here.
            </p>
          </div>
        )}

        {/* Streaming placeholder — shown while research is in progress but no blocks yet */}
        {blocks.length === 0 && phase === "streaming" && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-6 flex gap-1.5">
              <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-terracotta [animation-delay:0ms]" />
              <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-terracotta [animation-delay:150ms]" />
              <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-terracotta [animation-delay:300ms]" />
            </div>
            <p className="font-serif text-xl italic text-charcoal">
              Researching your idea...
            </p>
            <p className="mt-2 font-sans text-[14px] text-secondary">
              We&apos;re analyzing the market and finding competitors. This usually takes 15-30 seconds.
            </p>
          </div>
        )}

        {(blocks.length > 0 || blockErrors.length > 0) && (
          <div className="flex flex-col gap-4">
            {blocks.map((block) => (
              <ResearchBlock
                key={block.id}
                block={block}
                onRefine={onRefine}
                isRefining={isRefining}
              />
            ))}
            {blockErrors.map((err) => (
              <BlockErrorCard
                key={err.block_name + err.error_code}
                blockName={err.block_name}
                error={err.error}
                errorCode={err.error_code}
              />
            ))}
          </div>
        )}

        {waitingForCompetitors && competitorList && competitorList.length > 0 && (
          <div className="mt-6">
            <CompetitorSelector
              competitors={competitorList}
              selectedIds={selectedCompetitors}
              onSelectionChange={onCompetitorSelectionChange}
              onExplore={onExploreCompetitors}
              disabled={false}
            />
          </div>
        )}

        {waitingForProblems && problemAreas && problemAreas.length > 0 && (
          <div className="mt-6">
            <ProblemSelector
              problems={problemAreas}
              selectedIds={selectedProblems}
              onSelectionChange={onProblemSelectionChange}
              onDefine={onDefineProblems}
              disabled={false}
            />
          </div>
        )}
      </div>
    </div>
  );
}
