"use client";

interface ImportingViewProps {
  figmaUrl: string;
}

export function ImportingView({ figmaUrl }: ImportingViewProps) {
  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col flex-1">
      <div className="w-full mb-6">
        <div className="flex items-center gap-3 mb-2">
          <svg
            className="animate-spin h-4 w-4 text-terracotta"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth={4}
            />
            <path
              className="opacity-75"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              fill="currentColor"
            />
          </svg>
          <p className="text-sm font-medium text-charcoal">
            Importing your frame...
          </p>
        </div>
        <p className="text-xs text-charcoal-light truncate ml-7">
          {figmaUrl}
        </p>
      </div>

      {/* Skeleton frame preview */}
      <div className="flex-1 w-full min-h-[300px] bg-sand-light rounded-2xl border border-stone/50 overflow-hidden">
        <div className="h-full flex flex-col p-6 gap-4 animate-pulse">
          {/* Top bar skeleton */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-stone/40 rounded-lg" />
            <div className="h-4 w-32 bg-stone/40 rounded" />
            <div className="flex-1" />
            <div className="h-4 w-20 bg-stone/30 rounded" />
          </div>
          {/* Content skeleton */}
          <div className="flex gap-4 flex-1">
            <div className="flex-1 flex flex-col gap-3">
              <div className="h-5 w-48 bg-stone/40 rounded" />
              <div className="h-3 w-full bg-stone/30 rounded" />
              <div className="h-3 w-3/4 bg-stone/30 rounded" />
              <div className="h-3 w-5/6 bg-stone/30 rounded" />
              <div className="mt-auto flex gap-2">
                <div className="h-9 w-24 bg-stone/40 rounded-lg" />
                <div className="h-9 w-24 bg-stone/30 rounded-lg" />
              </div>
            </div>
            <div className="w-1/3 bg-stone/30 rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  );
}
