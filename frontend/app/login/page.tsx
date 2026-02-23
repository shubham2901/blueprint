"use client";

import { useState } from "react";
import Link from "next/link";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || isSubmitting) return;
    setIsSubmitting(true);
    // Auth flow deferred to V1 — UI shell only
    setTimeout(() => setIsSubmitting(false), 1000);
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-sand px-4">
      <div className="w-full max-w-[400px] flex flex-col items-center gap-8">
        {/* Logo */}
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-charcoal">
          <span className="font-sans text-sm font-bold text-workspace">B</span>
        </div>

        {/* Heading */}
        <div className="text-center">
          <h1 className="font-serif text-[28px] leading-tight text-charcoal md:text-[32px]">
            Log in to continue
          </h1>
          <p className="mx-auto mt-3 max-w-[320px] font-sans text-[15px] leading-relaxed text-secondary">
            Enter your email to access your research and blueprints.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
          <div>
            <label
              htmlFor="email"
              className="mb-1.5 block font-sans text-[13px] font-medium text-charcoal"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={isSubmitting}
              autoComplete="email"
              className="w-full rounded-input border border-border bg-workspace px-4 py-3 font-sans text-[15px] text-charcoal placeholder:text-placeholder shadow-subtle transition-colors focus:outline-none focus:ring-2 focus:ring-terracotta/30 disabled:opacity-50"
            />
          </div>

          <button
            type="submit"
            disabled={!email.trim() || isSubmitting}
            className="w-full rounded-button bg-terracotta px-4 py-3 font-sans text-[14px] font-medium text-workspace transition-opacity hover:opacity-95 disabled:opacity-40"
          >
            {isSubmitting ? "Signing in..." : "Log in"}
          </button>
        </form>

        {/* Cookie notice */}
        <p className="text-center font-sans text-[12px] leading-relaxed text-secondary">
          This site uses cookies for performance and personalization.{" "}
          <Link
            href="/"
            className="text-terracotta underline underline-offset-2 hover:opacity-90"
          >
            Cookie settings
          </Link>
        </p>

        {/* Back to home */}
        <Link
          href="/"
          className="font-sans text-[13px] text-secondary transition-colors hover:text-charcoal"
        >
          ← Back to home
        </Link>
      </div>
    </main>
  );
}
