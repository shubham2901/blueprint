"use client";

/**
 * Explore Workspace — Screens 2-6, 9
 *
 * Single SSE orchestration owner. ALL streaming happens here.
 * Manages the full ResearchState and dispatches events to child components.
 */

import { useEffect, useReducer, useRef, useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { startResearch, sendSelection, sendRefine, type SSEConnection } from "@/lib/api";
import type {
  ResearchState,
  ResearchEvent,
  ClarificationAnswer,
  CompetitorInfo,
  ProblemArea,
  StepName,
  RefineRequest,
} from "@/lib/types";
import { Sidebar } from "@/components/Sidebar";
import { Workspace } from "@/components/Workspace";

// ── Initial State ────────────────────────────────────────────

const initialState: ResearchState = {
  phase: "idle",
  journeyId: null,
  intentType: null,
  blocks: [],
  errors: [],
  clarificationQuestions: null,
  competitorList: null,
  selectedCompetitors: [],
  problemAreas: null,
  selectedProblems: [],
  currentStep: null,
  completedSteps: [],
  summary: null,
  quickResponse: null,
  fatalError: null,
};

// ── Reducer ──────────────────────────────────────────────────

type Action =
  | { type: "SSE_EVENT"; event: ResearchEvent }
  | { type: "SET_PHASE"; phase: ResearchState["phase"] }
  | { type: "SET_SELECTED_COMPETITORS"; ids: string[] }
  | { type: "SET_SELECTED_PROBLEMS"; ids: string[] }
  | { type: "RESTORE_STATE"; state: Partial<ResearchState> }
  | { type: "SET_REFINING"; isRefining: boolean };

function reducer(state: ResearchState, action: Action): ResearchState {
  switch (action.type) {
    case "SET_PHASE":
      return { ...state, phase: action.phase };

    case "SET_SELECTED_COMPETITORS":
      return { ...state, selectedCompetitors: action.ids };

    case "SET_SELECTED_PROBLEMS":
      return { ...state, selectedProblems: action.ids };

    case "RESTORE_STATE":
      return { ...state, ...action.state };

    case "SSE_EVENT": {
      const event = action.event;

      switch (event.type) {
        case "quick_response":
          return {
            ...state,
            phase: "completed",
            quickResponse: event.message,
          };

        case "journey_started":
          return {
            ...state,
            phase: "streaming",
            journeyId: event.journey_id,
            intentType: event.intent_type,
          };

        case "intent_redirect":
          return state; // Info only, no state change needed

        case "step_started":
          return {
            ...state,
            phase: "streaming",
            currentStep: event.step as StepName,
          };

        case "step_completed":
          return {
            ...state,
            currentStep: null,
            completedSteps: state.completedSteps.includes(
              event.step as StepName,
            )
              ? state.completedSteps
              : [...state.completedSteps, event.step as StepName],
          };

        case "block_ready": {
          const block = event.block;
          const newBlocks = [...state.blocks, block];
          let extras: Partial<ResearchState> = {};

          // Extract competitors from competitor_list block
          if (
            block.type === "competitor_list" &&
            block.output_data?.competitors
          ) {
            extras.competitorList =
              block.output_data.competitors as CompetitorInfo[];
          }

          // Extract problems from gap_analysis block
          if (block.type === "gap_analysis" && block.output_data?.problems) {
            extras.problemAreas =
              block.output_data.problems as ProblemArea[];
          }

          return { ...state, blocks: newBlocks, ...extras };
        }

        case "block_error":
          return {
            ...state,
            errors: [...state.errors, event],
          };

        case "clarification_needed":
          return {
            ...state,
            phase: "waiting_for_clarification",
            clarificationQuestions: event.questions,
          };

        case "waiting_for_selection": {
          const phaseMap: Record<string, ResearchState["phase"]> = {
            clarification: "waiting_for_clarification",
            competitors: "waiting_for_competitors",
            problems: "waiting_for_problems",
          };
          return {
            ...state,
            phase: phaseMap[event.selection_type] || state.phase,
          };
        }

        case "research_complete":
          return {
            ...state,
            phase: "completed",
            summary: event.summary,
            journeyId: event.journey_id || state.journeyId,
          };

        case "error":
          return {
            ...state,
            phase: "error",
            fatalError: {
              message: event.message,
              errorCode: event.error_code,
              recoverable: event.recoverable,
            },
          };

        case "refine_started":
          return state; // Handled by isRefining state

        case "refine_complete":
          return state; // Handled by isRefining state

        default:
          return state;
      }
    }

    default:
      return state;
  }
}

// ── Page Component ───────────────────────────────────────────

export default function ExplorePage() {
  const params = useParams();
  const router = useRouter();
  const journeyIdParam = params.journeyId as string;

  const [state, dispatch] = useReducer(reducer, initialState);
  const [isRefining, setIsRefining] = useState(false);
  const sseRef = useRef<SSEConnection | null>(null);
  const refineRef = useRef<SSEConnection | null>(null);
  const hasStartedRef = useRef(false);
  const cleanupTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Event handler ──────────────────────────────────────
  const handleEvent = useCallback(
    (event: ResearchEvent) => {
      dispatch({ type: "SSE_EVENT", event });

      // Replace URL when journey is created.
      if (event.type === "journey_started" && journeyIdParam === "new") {
        window.history.replaceState(null, "", `/research/explore/${event.journey_id}`);
      }
    },
    [journeyIdParam],
  );

  const handleError = useCallback((error: Error) => {
    console.error("SSE Error:", error);
    dispatch({ type: "SET_PHASE", phase: "error" });
  }, []);

  const handleComplete = useCallback(() => {
    sseRef.current = null;
  }, []);

  // ── Redirect to research landing on page reload (no restorable state in V0) ──
  useEffect(() => {
    if (journeyIdParam !== "new") {
      router.replace("/research");
      return;
    }

    if (!hasStartedRef.current) {
      const prompt =
        sessionStorage.getItem("bp_pending_prompt") ||
        new URLSearchParams(window.location.search).get("prompt");
      if (!prompt) {
        router.replace("/research");
        return;
      }
      sessionStorage.removeItem("bp_pending_prompt");
      hasStartedRef.current = true;
      dispatch({ type: "SET_PHASE", phase: "streaming" });
      sseRef.current = startResearch(
        prompt,
        handleEvent,
        handleError,
        handleComplete,
      );
    }
  }, [journeyIdParam, router, handleEvent, handleError, handleComplete]);

  // ── StrictMode-safe SSE cleanup ───────────────────────
  useEffect(() => {
    if (cleanupTimerRef.current) {
      clearTimeout(cleanupTimerRef.current);
      cleanupTimerRef.current = null;
    }
    return () => {
      const sse = sseRef.current;
      cleanupTimerRef.current = setTimeout(() => {
        sse?.close();
      }, 50);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Selection handlers ─────────────────────────────────

  const handleClarificationSubmit = useCallback(
    (answers: ClarificationAnswer[]) => {
      if (!state.journeyId) return;
      dispatch({ type: "SET_PHASE", phase: "streaming" });
      sseRef.current = sendSelection(
        state.journeyId,
        {
          step_type: "clarify",
          selection: { answers },
        },
        handleEvent,
        handleError,
        handleComplete,
      );
    },
    [state.journeyId, handleEvent, handleError, handleComplete],
  );

  const handleExploreCompetitors = useCallback(
    (competitorIds: string[]) => {
      if (!state.journeyId) return;
      dispatch({ type: "SET_PHASE", phase: "streaming" });
      sseRef.current = sendSelection(
        state.journeyId,
        {
          step_type: "select_competitors",
          selection: { competitor_ids: competitorIds },
        },
        handleEvent,
        handleError,
        handleComplete,
      );
    },
    [state.journeyId, handleEvent, handleError, handleComplete],
  );

  const handleDefineProblems = useCallback(
    (problemIds: string[]) => {
      if (!state.journeyId) return;
      dispatch({ type: "SET_PHASE", phase: "streaming" });
      sseRef.current = sendSelection(
        state.journeyId,
        {
          step_type: "select_problems",
          selection: { problem_ids: problemIds },
        },
        handleEvent,
        handleError,
        handleComplete,
      );
    },
    [state.journeyId, handleEvent, handleError, handleComplete],
  );

  const handleNewPrompt = useCallback(
    (prompt: string) => {
      sessionStorage.setItem("bp_pending_prompt", prompt);
      router.push("/research/explore/new");
    },
    [router],
  );

  const handleRefine = useCallback(
    (stepType: RefineRequest["step_type"], feedback?: string) => {
      if (!state.journeyId || isRefining) return;
      
      setIsRefining(true);
      refineRef.current = sendRefine(
        state.journeyId,
        { step_type: stepType, feedback },
        handleEvent,
        (error) => {
          console.error("Refine Error:", error);
          setIsRefining(false);
        },
        () => {
          setIsRefining(false);
          refineRef.current = null;
        },
      );
    },
    [state.journeyId, isRefining, handleEvent],
  );

  // ── Render ─────────────────────────────────────────────

  return (
    <main className="flex h-screen bg-sand p-3 gap-3">
      <div className="flex-[7] min-w-0">
        <Workspace
          blocks={state.blocks}
          blockErrors={state.errors}
          phase={state.phase}
          fatalError={state.fatalError}
          competitorList={state.competitorList}
          selectedCompetitors={state.selectedCompetitors}
          onCompetitorSelectionChange={(ids: string[]) =>
            dispatch({ type: "SET_SELECTED_COMPETITORS", ids })
          }
          onExploreCompetitors={handleExploreCompetitors}
          problemAreas={state.problemAreas}
          selectedProblems={state.selectedProblems}
          onProblemSelectionChange={(ids: string[]) =>
            dispatch({ type: "SET_SELECTED_PROBLEMS", ids })
          }
          onDefineProblems={handleDefineProblems}
          onStartNew={() => router.push("/research")}
          onRefine={handleRefine}
          isRefining={isRefining}
        />
      </div>

      <div className="flex-[3] min-w-[320px]">
        <Sidebar
          researchState={state}
          onSubmitPrompt={handleNewPrompt}
          onSubmitClarification={handleClarificationSubmit}
          onSelectCompetitors={handleExploreCompetitors}
          onSelectProblems={handleDefineProblems}
        />
      </div>
    </main>
  );
}
