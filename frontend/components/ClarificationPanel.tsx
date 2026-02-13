"use client";

import { useState, useCallback } from "react";
import type { ClarificationQuestion, ClarificationAnswer, ClarificationOption } from "@/lib/types";

interface ClarificationPanelProps {
  questions: ClarificationQuestion[];
  onSubmit: (answers: ClarificationAnswer[]) => void;
  disabled?: boolean;
}

// Special ID for the "Other" option
const OTHER_OPTION_ID = "__other__";

export function ClarificationPanel({
  questions,
  onSubmit,
  disabled = false,
}: ClarificationPanelProps) {
  // Track selected option IDs per question
  const [selections, setSelections] = useState<Record<string, string[]>>(() => {
    const init: Record<string, string[]> = {};
    questions.forEach((q) => (init[q.id] = []));
    return init;
  });
  
  // Track "Other" text input per question
  const [otherTexts, setOtherTexts] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    questions.forEach((q) => (init[q.id] = ""));
    return init;
  });

  const handleOptionClick = useCallback(
    (questionId: string, optionId: string, allowMultiple: boolean) => {
      setSelections((prev) => {
        const current = prev[questionId] ?? [];
        const has = current.includes(optionId);
        
        // If clicking "Other", just toggle it
        if (optionId === OTHER_OPTION_ID) {
          const next = has
            ? current.filter((id) => id !== optionId)
            : allowMultiple
              ? [...current, optionId]
              : [optionId];
          return { ...prev, [questionId]: next };
        }
        
        // For regular options
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

  const handleOtherTextChange = useCallback((questionId: string, text: string) => {
    setOtherTexts((prev) => ({ ...prev, [questionId]: text }));
  }, []);

  // Check if question is answered (has selections OR has "Other" with text)
  const isQuestionAnswered = (q: ClarificationQuestion): boolean => {
    const selected = selections[q.id] ?? [];
    const hasOtherSelected = selected.includes(OTHER_OPTION_ID);
    const otherText = otherTexts[q.id] ?? "";
    
    // If "Other" is selected, must have text
    if (hasOtherSelected) {
      return otherText.trim().length > 0;
    }
    // Otherwise, must have at least one regular selection
    return selected.length > 0;
  };

  const answeredCount = questions.filter(isQuestionAnswered).length;
  const allAnswered = questions.every(isQuestionAnswered);

  const handleSubmit = useCallback(() => {
    if (allAnswered && !disabled) {
      const answers: ClarificationAnswer[] = questions.map((q) => {
        const selected = selections[q.id] ?? [];
        const hasOther = selected.includes(OTHER_OPTION_ID);
        const regularSelections = selected.filter((id) => id !== OTHER_OPTION_ID);
        
        return {
          question_id: q.id,
          selected_option_ids: regularSelections,
          other_text: hasOther ? otherTexts[q.id]?.trim() : undefined,
        };
      });
      onSubmit(answers);
    }
  }, [questions, selections, otherTexts, allAnswered, disabled, onSubmit]);

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

      {questions.map((question) => {
        const hasOtherSelected = selections[question.id]?.includes(OTHER_OPTION_ID);
        
        return (
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
              {/* Render "Other" option if allow_other is true */}
              {question.allow_other && (
                <OptionChip
                  option={{ id: OTHER_OPTION_ID, label: "Other", description: "" }}
                  selected={hasOtherSelected ?? false}
                  onToggle={() =>
                    handleOptionClick(question.id, OTHER_OPTION_ID, question.allow_multiple)
                  }
                  disabled={disabled}
                />
              )}
            </div>
            {/* Show text input when "Other" is selected */}
            {question.allow_other && hasOtherSelected && (
              <input
                type="text"
                placeholder="Please specify..."
                value={otherTexts[question.id] ?? ""}
                onChange={(e) => handleOtherTextChange(question.id, e.target.value)}
                disabled={disabled}
                className="mt-2 w-full rounded-card border border-border bg-workspace px-3 py-2 font-sans text-[13px] text-charcoal placeholder:text-secondary focus:border-terracotta focus:outline-none disabled:opacity-50"
                autoFocus
              />
            )}
          </div>
        );
      })}

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
