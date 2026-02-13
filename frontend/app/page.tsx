"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";

const SUGGESTED_PILLS = [
  { label: "Build a product", prefill: "I want to build a " },
  { label: "Explore a market", prefill: "Tell me about " },
  { label: "Competitor deep dive", prefill: "Tell me about " },
  { label: "Find my niche", prefill: "I want to build something in the  space" },
] as const;

export default function LandingPage() {
  const [prompt, setPrompt] = useState("");
  const [isNavigating, setIsNavigating] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const router = useRouter();

  const handleSubmit = () => {
    const trimmed = prompt.trim();
    if (!trimmed || isNavigating) return;
    setIsNavigating(true);
    // Store prompt in sessionStorage instead of URL to avoid length limits
    sessionStorage.setItem("bp_pending_prompt", trimmed);
    router.push("/explore/new");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handlePillClick = (prefill: string) => {
    setPrompt(prefill);
    inputRef.current?.focus();
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-sand px-4">
      <div className="w-full max-w-[640px] flex flex-col items-center gap-8">
        {/* Logo */}
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-charcoal">
          <span className="font-sans text-sm font-bold text-workspace">B</span>
        </div>

        {/* Heading */}
        <div className="text-center">
          <h1 className="font-serif text-[28px] leading-tight text-charcoal md:text-[32px]">
            What would you like to build?
          </h1>
          <p className="mx-auto mt-3 max-w-[480px] font-sans text-[15px] leading-relaxed text-secondary">
            Describe a product idea or market you&apos;re curious about.
            Blueprint will map the competitive landscape, find gaps, and help
            you define what to build.
          </p>
        </div>

        {/* Prompt Input */}
        <div className="relative w-full rounded-input border border-border bg-workspace shadow-subtle">
          <textarea
            ref={inputRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g., I want to build a note-taking app for students..."
            disabled={isNavigating}
            rows={3}
            className="w-full resize-none rounded-input bg-transparent px-4 pt-4 pb-12 font-sans text-[15px] text-charcoal placeholder:text-placeholder focus:outline-none disabled:opacity-50"
          />
          <div className="absolute right-3 bottom-3">
            <button
              onClick={handleSubmit}
              disabled={!prompt.trim() || isNavigating}
              className="rounded-button bg-charcoal px-4 py-1.5 font-sans text-[13px] font-medium text-workspace transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {isNavigating ? "Starting..." : "RUN"}
            </button>
          </div>
        </div>

        {/* Suggested Research Pills */}
        <div className="flex flex-wrap justify-center gap-2">
          {SUGGESTED_PILLS.map((pill) => (
            <button
              key={pill.label}
              onClick={() => handlePillClick(pill.prefill)}
              disabled={isNavigating}
              className="rounded-chip border border-border bg-workspace px-4 py-1.5 font-sans text-[13px] text-secondary transition-colors hover:bg-sand disabled:opacity-50"
            >
              {pill.label}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
