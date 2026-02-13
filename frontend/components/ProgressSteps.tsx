import type { StepName } from "@/lib/types";

const STEP_LABELS: Record<StepName, string> = {
  classifying: "Understanding your query",
  clarifying: "Clarifying",
  finding_competitors: "Finding competitors",
  exploring: "Analyzing products",
  gap_analyzing: "Finding market gaps",
  defining_problem: "Defining your problem",
};

const EXPLORE_STEPS: StepName[] = ["classifying", "finding_competitors", "exploring"];
const BUILD_STEPS: StepName[] = [
  "classifying",
  "finding_competitors",
  "exploring",
  "gap_analyzing",
  "defining_problem",
];

interface ProgressStepsProps {
  intentType: "build" | "explore" | null;
  currentStep: string | null;
  completedSteps: string[];
  waitingForSelection: boolean;
}

export function ProgressSteps({
  intentType,
  currentStep,
  completedSteps,
  waitingForSelection,
}: ProgressStepsProps) {
  const steps = intentType === "build" ? BUILD_STEPS : intentType === "explore" ? EXPLORE_STEPS : [];

  if (steps.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {steps.map((step) => {
        const isCompleted = completedSteps.includes(step);
        const isCurrent = currentStep === step || (waitingForSelection && completedSteps[completedSteps.length - 1] === step && step === steps[steps.length - 1]);

        return (
          <div key={step} className="flex items-center gap-3">
            <div className="flex h-5 w-5 shrink-0 items-center justify-center">
              {isCompleted ? (
                <span className="text-success text-sm" aria-hidden="true">
                  ✓
                </span>
              ) : isCurrent ? (
                <span
                  className="h-2 w-2 animate-pulse rounded-full bg-terracotta"
                  aria-hidden="true"
                />
              ) : (
                <span
                  className="h-2 w-2 rounded-full border border-placeholder bg-transparent"
                  aria-hidden="true"
                />
              )}
            </div>
            <span
              className={`font-sans text-[13px] ${
                isCurrent ? "font-medium text-charcoal" : isCompleted ? "text-secondary" : "text-placeholder"
              }`}
            >
              {STEP_LABELS[step]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
