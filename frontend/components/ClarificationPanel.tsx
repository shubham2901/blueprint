"use client";

import { useState, useCallback } from "react";
import type { ClarificationQuestion, ClarificationAnswer, ClarificationOption } from "@/lib/types";

interface ClarificationPanelProps {
  questions: ClarificationQuestion[];
  onSubmit: (answers: ClarificationAnswer[]) => void;
  disabled?: boolean;
}

export function ClarificationPanel({
  questions,
  onSubmit,
  disabled = false,
}: ClarificationPanelProps) {
  const [selections, setSelections] = useState<Record<string, string[]>>(() => {
    const init: Record<string, string[]> = {};
    questions.forEach((q) => (init[q.id] = []));
    return init;
  });

  const handleOptionClick = useCallback(
    (questionId: string, optionId: string, allowMultiple: boolean) => {
      setSelections((prev) => {
        const current = prev[questionId] ?? [];
        const has = current.includes(optionId);
        const next = allowMultiple
          ? has
            ? current.filter((id) => id !== optionId)
            : [...current, optionId]
          : has
            ? current
            : [optionId];
        return { ...prev, [questionId]: next };
      });
    },
    []
  );

  const answeredCount = questions.filter((q) => (selections[q.id]?.length ?? 0) > 0).length;
  const allAnswered = questions.every((q) => (selections[q.id]?.length ?? 0) > 0);

  const handleSubmit = useCallback(() => {
    if (allAnswered && !disabled) {
      const answers: ClarificationAnswer[] = questions.map((q) => ({
        question_id: q.id,
        selected_option_ids: selections[q.id] ?? [],
      }));
      onSubmit(answers);
    }
  }, [questions, selections, allAnswered, disabled, onSubmit]);

  return (
    <div className="flex flex-col gap-5">
      {/* Section heading */}
      <div>
        <h3 className="font-serif text-[18px] leading-snug text-charcoal">
          A few quick questions
        </h3>
        <p className="mt-1 font-sans text-[13px] text-secondary">
          Help us narrow down the research. {answeredCount} of {questions.length} answered.
        </p>
      </div>

      {questions.map((question) => (
        <div key={question.id} className="flex flex-col gap-2">
          <p className="font-sans text-[14px] font-medium text-charcoal">{question.label}</p>
          <div className="flex flex-wrap gap-2">
            {question.options.map((opt) => (
              <OptionChip
                key={opt.id}
                option={opt}
                selected={selections[question.id]?.includes(opt.id) ?? false}
                onToggle={() =>
                  handleOptionClick(question.id, opt.id, question.allow_multiple)
                }
                disabled={disabled}
              />
            ))}
          </div>
        </div>
      ))}

      <button
        onClick={handleSubmit}
        disabled={!allAnswered || disabled}
        className="w-fit rounded-button bg-terracotta px-4 py-2 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90 disabled:opacity-40"
      >
        Continue
      </button>
    </div>
  );
}

function OptionChip({
  option,
  selected,
  onToggle,
  disabled,
}: {
  option: ClarificationOption;
  selected: boolean;
  onToggle: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      className={`rounded-chip border px-4 py-1.5 font-sans text-[13px] transition-colors disabled:opacity-50 ${
        selected
          ? "border-terracotta bg-terracotta-light text-charcoal"
          : "border-border bg-workspace text-secondary hover:bg-sand"
      }`}
    >
      {option.label}
    </button>
  );
}
