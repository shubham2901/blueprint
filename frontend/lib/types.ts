/**
 * Blueprint — Frontend Type Definitions
 *
 * Mirrors backend/app/models.py. Single source of truth for frontend type safety.
 * When backend models change, update this file to match.
 */

// ──────────────────────────────────────────────────────
// SSE Event Types
// ──────────────────────────────────────────────────────

export type IntentType = "build" | "explore";
export type StepName =
  | "classifying"
  | "clarifying"
  | "finding_competitors"
  | "exploring"
  | "gap_analyzing"
  | "defining_problem";
export type SelectionType = "clarification" | "competitors" | "problems";
export type BlockType =
  | "market_overview"
  | "competitor_list"
  | "product_profile"
  | "gap_analysis"
  | "problem_statement";

export type ResearchEvent =
  | JourneyStartedEvent
  | QuickResponseEvent
  | IntentRedirectEvent
  | StepStartedEvent
  | StepCompletedEvent
  | BlockReadyEvent
  | BlockErrorEvent
  | ClarificationNeededEvent
  | WaitingForSelectionEvent
  | ResearchCompleteEvent
  | RefineStartedEvent
  | RefineCompleteEvent
  | ErrorEvent;

export interface JourneyStartedEvent {
  type: "journey_started";
  journey_id: string;
  intent_type: IntentType;
}

export interface QuickResponseEvent {
  type: "quick_response";
  message: string;
}

export interface IntentRedirectEvent {
  type: "intent_redirect";
  original_intent: string;
  redirected_to: string;
  message: string;
}

export interface StepStartedEvent {
  type: "step_started";
  step: StepName;
  label: string;
}

export interface StepCompletedEvent {
  type: "step_completed";
  step: StepName;
}

export interface BlockReadyEvent {
  type: "block_ready";
  block: ResearchBlock;
}

export interface BlockErrorEvent {
  type: "block_error";
  block_name: string;
  error: string;
  error_code: string; // User-facing ref code, e.g., "BP-3F8A2C"
}

export interface ClarificationNeededEvent {
  type: "clarification_needed";
  questions: ClarificationQuestion[];
}

export interface WaitingForSelectionEvent {
  type: "waiting_for_selection";
  selection_type: SelectionType;
}

export interface ResearchCompleteEvent {
  type: "research_complete";
  journey_id: string;
  summary: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
  recoverable: boolean;
  error_code: string; // User-facing ref code, e.g., "BP-3F8A2C"
}

export interface RefineStartedEvent {
  type: "refine_started";
  step_type: string;
  message: string;
}

export interface RefineCompleteEvent {
  type: "refine_complete";
  step_type: string;
}

// ──────────────────────────────────────────────────────
// Block Types
// ──────────────────────────────────────────────────────

export interface ResearchBlock {
  id: string;
  type: BlockType;
  title: string;
  content: string; // Markdown-formatted (for display)
  output_data?: Record<string, unknown>; // Typed structured data (for programmatic use)
  // output_data shape depends on block type:
  //   competitor_list:    { competitors: CompetitorInfo[] }
  //   gap_analysis:       { problems: ProblemArea[] }
  //   product_profile:    { profile: ProductProfile }
  //   problem_statement:  { statement: ProblemStatement }
  //   market_overview:    { overview: MarketOverview }
  sources: string[];
  cached: boolean;
  cached_at?: string; // ISO date string
}

export interface ClarificationQuestion {
  id: string;
  label: string;
  options: ClarificationOption[];
  allow_multiple: boolean;
  allow_other: boolean; // If true, show "Other" option with text input
}

export interface ClarificationOption {
  id: string; // Stable slug ID, e.g., "mobile", "web", "text-notes"
  label: string; // Display label
  description: string;
}

// ──────────────────────────────────────────────────────
// Competitor Types (from competitor_list block)
// ──────────────────────────────────────────────────────

export interface CompetitorInfo {
  id: string; // Slug: "notion", "google-docs"
  name: string;
  description: string;
  url?: string;
  category?: string;
  pricing_model?: string;
}

// ──────────────────────────────────────────────────────
// Journey Types (from journey endpoints)
// ──────────────────────────────────────────────────────

export interface JourneySummary {
  id: string;
  title: string | null;
  status: string; // "active" | "completed" | "archived"
  intent_type: IntentType;
  initial_prompt: string;
  created_at: string; // ISO date string
  updated_at: string;
  step_count: number;
}

export interface JourneyDetail {
  id: string;
  title: string | null;
  status: string;
  intent_type: IntentType;
  initial_prompt: string;
  steps: JourneyStep[];
  created_at: string;
  updated_at: string;
}

export interface JourneyStep {
  id: string;
  step_number: number;
  step_type: string; // "classify" | "clarify" | "find_competitors" | "select_competitors" | "explore" | "select_problems" | "define_problem"
  input_data: Record<string, unknown> | null;
  output_data: Record<string, unknown> | null;
  user_selection: Record<string, unknown> | null;
  created_at: string;
}

// ──────────────────────────────────────────────────────
// API Response Types
// ──────────────────────────────────────────────────────

export interface JourneyListResponse {
  journeys: JourneySummary[];
}

export interface JourneyDetailResponse {
  journey: JourneyDetail;
}

// ──────────────────────────────────────────────────────
// Request Types
// ──────────────────────────────────────────────────────

export interface ResearchRequest {
  prompt: string;
}

export interface ClarificationAnswer {
  question_id: string;
  selected_option_ids: string[]; // Option ID slugs, e.g., ["mobile", "web"]
  other_text?: string; // Free-form text when user selects "Other"
}

export interface ClarificationSelection {
  answers: ClarificationAnswer[];
}

export interface CompetitorSelection {
  competitor_ids: string[];
}

export interface ProblemSelection {
  problem_ids: string[];
}

export interface SelectionRequest {
  step_type: "clarify" | "select_competitors" | "select_problems";
  selection: ClarificationSelection | CompetitorSelection | ProblemSelection;
}

export interface RefineRequest {
  step_type: "find_competitors" | "explore" | "gap_analysis" | "define_problem";
  feedback?: string;
}

// ──────────────────────────────────────────────────────
// UI State Types (frontend-only, not from backend)
// ──────────────────────────────────────────────────────

export type ResearchPhase =
  | "idle" // No research in progress
  | "streaming" // SSE stream is active
  | "waiting_for_clarification" // Multi-question clarification shown, waiting for user
  | "waiting_for_competitors" // Competitor checkboxes shown, waiting for user
  | "waiting_for_problems" // Problem checkboxes shown (build intent), waiting for user
  | "completed" // Research done
  | "error"; // Fatal error

export interface FatalError {
  message: string;
  errorCode: string;
  recoverable: boolean;
}

export interface ResearchState {
  phase: ResearchPhase;
  journeyId: string | null;
  intentType: IntentType | null;
  blocks: ResearchBlock[];
  errors: BlockErrorEvent[];
  clarificationQuestions: ClarificationQuestion[] | null;
  competitorList: CompetitorInfo[] | null;
  selectedCompetitors: string[]; // IDs of checked competitors
  problemAreas: ProblemArea[] | null; // From gap_analysis block (build intent)
  selectedProblems: string[]; // IDs of selected problems
  currentStep: StepName | null;
  completedSteps: StepName[];
  summary: string | null;
  quickResponse: string | null; // For small_talk/off_topic (no journey)
  fatalError: FatalError | null; // For non-recoverable SSE errors
}

// Problem area from gap analysis (extracted from gap_analysis block's output_data.problems)
export interface ProblemArea {
  id: string;
  title: string;
  description: string;
  evidence: string[];
  opportunity_size?: string;
}

// Product profile (unused in types.ts directly but useful for output_data typing)
export interface ProductProfile {
  name: string;
  description: string;
  url: string;
  features: string[];
  strengths: string[];
  weaknesses: string[];
  pricing_tiers: string[];
  reddit_sentiment: string;
}

// Market overview (from market_overview block)
export interface MarketOverview {
  summary: string;
  trends: string[];
  key_players: string[];
}

// Problem statement (from problem_statement block)
export interface ProblemStatement {
  title: string;
  problem: string;
  target_user: string;
  value_proposition: string;
  key_differentiators: string[];
}
