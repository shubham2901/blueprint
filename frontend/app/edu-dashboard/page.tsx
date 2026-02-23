"use client";

import { useState } from "react";

/* ── Figma Design Implementation (node 1:13009) ─────────────────────────────
 * Educational Dashboard — General-playground
 * Design tokens from get_variable_defs; layout from get_screenshot
 */

const NAV_ITEMS: Array<{
  id: string;
  label: string;
  active?: boolean;
  icon: React.ComponentType<{ active?: boolean }>;
}> = [
  { id: "home", label: "Home", active: true, icon: HomeIcon },
  { id: "study", label: "Study", icon: StudyIcon },
  { id: "doubts", label: "Doubts", icon: DoubtsIcon },
  { id: "tests", label: "Tests", icon: TestsIcon },
  { id: "break", label: "Break", icon: BreakIcon },
];

const SCHEDULE_FILTERS = ["Today", "Tomorrow", "Day after tomorrow"] as const;
const HOMEWORK_FILTERS = ["Assigned today", "Due today"] as const;

function HomeIcon({ active }: { active?: boolean }) {
  const color = active ? "#3592fd" : "#5c5c5c";
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  );
}

function StudyIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      <line x1="8" y1="6" x2="16" y2="6" />
      <line x1="8" y1="10" x2="16" y2="10" />
    </svg>
  );
}

function DoubtsIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function TestsIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}

function BreakIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#5c5c5c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function CalendarIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

function ChevronRightIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3592fd" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function LocationIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#bcbdbd" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

export default function EduDashboardPage() {
  const [scheduleFilter, setScheduleFilter] = useState<(typeof SCHEDULE_FILTERS)[number]>("Today");
  const [homeworkFilter, setHomeworkFilter] = useState<(typeof HOMEWORK_FILTERS)[number]>("Assigned today");

  return (
    <div className="mx-auto flex min-h-screen max-w-[390px] flex-col bg-[#0f0f0f] pb-20">
      {/* Status bar placeholder */}
      <div className="h-11 shrink-0" />

      {/* Header */}
      <header className="flex items-start justify-between px-4 pt-2">
        <div>
          <div className="flex gap-2">
            {["11TH", "JEE ADV", "LIVE"].map((tag) => (
              <span
                key={tag}
                className="rounded-lg bg-[#212121] px-3 py-1.5 text-xs font-semibold text-white"
              >
                {tag}
              </span>
            ))}
          </div>
          <button className="mt-2 flex items-center gap-1 text-sm text-[#3592fd]">
            Change course
            <ChevronRightIcon />
          </button>
        </div>
        <div className="flex gap-4">
          <button aria-label="Notifications">
            <BellIcon />
          </button>
          <button aria-label="Profile">
            <UserIcon />
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 pt-6">
        {/* Schedule */}
        <section className="mb-6">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">Schedule</h2>
            <button className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#212121]">
              <CalendarIcon />
            </button>
          </div>
          <div className="mb-4 flex gap-2">
            {SCHEDULE_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setScheduleFilter(f)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  scheduleFilter === f
                    ? "bg-white text-[#0f0f0f]"
                    : "bg-[#212121] text-[#848484]"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="min-w-[280px] shrink-0 overflow-hidden rounded-2xl border border-[#2e2e2e] bg-[#212121]"
              >
                <div className="flex h-32 items-center justify-center bg-[#3592fd]/20">
                  <div className="h-16 w-16 rounded-lg bg-[#3592fd]/40" />
                </div>
                <div className="p-4">
                  <h3 className="text-base font-semibold text-white">
                    Current electricity
                  </h3>
                  <p className="mt-1 text-sm text-[#bcbdbd]">
                    Started at 05:00 PM
                  </p>
                  <button className="mt-3 w-full rounded-xl border border-[#3592fd] py-2.5 text-sm font-medium text-[#3592fd]">
                    View details
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Stuck between 100-150 */}
        <section className="mb-6">
          <div className="rounded-2xl border border-[#2e2e2e] bg-[#212121] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-white">
                Stuck between 100-150
              </h2>
              <span className="rounded-full bg-[#f5a623]/15 px-2.5 py-0.5 text-[11px] font-semibold text-[#f5a623]">
                3 topics
              </span>
            </div>
            <p className="mb-4 text-xs text-[#848484]">
              These topics are holding you back. A focused plan can help.
            </p>
            <div className="flex flex-col gap-2.5">
              {[
                { name: "Rotational Motion", score: 112 },
                { name: "Electromagnetic Induction", score: 134 },
                { name: "Chemical Bonding", score: 148 },
              ].map((topic, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-[#181818] px-3.5 py-3"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#2e3357]">
                      <span className="text-xs font-bold text-[#3592fd]">
                        {i + 1}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-white">
                      {topic.name}
                    </span>
                  </div>
                  <span className="text-sm font-bold text-[#f5a623]">
                    {topic.score}
                  </span>
                </div>
              ))}
            </div>
            <button className="mt-4 w-full rounded-xl bg-[#3592fd] py-3 text-sm font-semibold text-white transition-colors hover:bg-[#2a7de6] active:bg-[#1f6dd4]">
              Create my plan
            </button>
          </div>
        </section>

        {/* Upcoming tests */}
        <section className="mb-6">
          <h2 className="mb-4 text-base font-semibold text-white">
            Upcoming tests
          </h2>
          <div className="flex overflow-hidden rounded-2xl border border-[#2e2e2e] bg-[#212121]">
            <div className="flex w-20 shrink-0 flex-col items-center justify-center bg-[#2e3357] p-3">
              <span className="text-sm font-bold text-white">12 Oct</span>
              <span className="mt-1 rounded-full bg-[#3592fd]/30 px-2 py-0.5 text-[10px] font-semibold text-[#3592fd]">
                CENTRE
              </span>
            </div>
            <div className="flex-1 p-4">
              <h3 className="text-base font-semibold text-white">
                Major test 1
              </h3>
              <p className="mt-1 text-sm text-[#bcbdbd]">
                12:0PM - 3:00PM
              </p>
              <div className="mt-2 flex items-center gap-1.5 text-sm text-[#bcbdbd]">
                <LocationIcon />
                Jayanagar centre
              </div>
              <button className="mt-3 flex items-center gap-1 text-sm font-medium text-[#3592fd]">
                View details
                <ChevronRightIcon />
              </button>
            </div>
          </div>
        </section>

        {/* Homework for you */}
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">
              Homework for you
            </h2>
            <button className="flex items-center gap-1 text-sm font-medium text-[#3592fd]">
              View all
              <ChevronRightIcon />
            </button>
          </div>
          <div className="mb-4 flex gap-2">
            {HOMEWORK_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setHomeworkFilter(f)}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  homeworkFilter === f
                    ? "bg-white text-[#0f0f0f]"
                    : "bg-[#212121] text-[#848484]"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="flex gap-4 overflow-x-auto pb-2">
            {[
              {
                title: "Parallel and Perpendicular Axis Theorem",
                topic: "Rotational Motion",
                details: "19 Qs • Due by March 6",
              },
              {
                title: "Parallel and Perpendicular Axis Theorem",
                topic: "Rotational Motion",
                details: "19 Qs • Due by March 6",
              },
            ].map((hw, i) => (
              <div
                key={i}
                className="min-w-[280px] shrink-0 rounded-2xl border border-[#2e2e2e] bg-[#212121] p-4"
              >
                <div className="flex justify-between">
                  <div className="flex-1 pr-2">
                    <h3 className="text-sm font-semibold text-white">
                      {hw.title}
                    </h3>
                    <p className="mt-1 text-xs text-[#bcbdbd]">{hw.topic}</p>
                    <p className="mt-1 text-xs text-[#848484]">{hw.details}</p>
                  </div>
                  <div className="h-10 w-10 shrink-0 rounded-lg bg-gradient-to-br from-[#3592fd] via-[#4949ee] to-[#f5a623]" />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 flex justify-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-white" />
            <span className="h-1.5 w-1.5 rounded-full bg-[#5c5c5c]" />
            <span className="h-1.5 w-1.5 rounded-full bg-[#5c5c5c]" />
          </div>
        </section>
      </main>

      {/* Bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 mx-auto flex max-w-[390px] items-center justify-around border-t border-[#2e2e2e] bg-[#0f0f0f] py-2">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className="flex flex-col items-center gap-1"
            aria-current={item.active === true ? "page" : undefined}
          >
            <item.icon active={item.active === true} />
            <span
              className={`text-[10px] ${
                item.active ? "text-[#3592fd] font-medium" : "text-[#848484]"
              }`}
            >
              {item.label}
            </span>
            {item.active && (
              <span className="h-0.5 w-6 rounded-full bg-[#3592fd]" />
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
