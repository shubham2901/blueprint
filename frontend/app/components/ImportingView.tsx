"use client";

/**
 * Importing View — Loading state during Figma import
 *
 * URL readonly, Import button disabled with spinner, skeleton loading area.
 */

interface ImportingViewProps {
  figmaUrl: string;
}

export function ImportingView({ figmaUrl }: ImportingViewProps) {
  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col flex-1">
      <div className="w-full mb-8">
        <label
          className="block text-xs font-semibold text-charcoal-light uppercase tracking-wider mb-2 ml-1"
          htmlFor="figma-url-importing"
        >
          Figma frame URL
        </label>
        <div className="flex items-center gap-2">
          <input
            id="figma-url-importing"
            type="text"
            value={figmaUrl}
            readOnly
            className="flex-1 w-full bg-sand-light border border-stone rounded-xl px-4 py-3 text-sm text-charcoal outline-none transition-all cursor-default"
          />
          <button
            type="button"
            disabled
            className="bg-terracotta/60 text-white px-8 py-3 rounded-xl text-sm font-semibold flex items-center gap-2 cursor-not-allowed"
          >
            <svg
              className="animate-spin h-4 w-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
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
            Importing
          </button>
        </div>
        <p className="mt-4 text-charcoal-light text-sm font-sans ml-1">
          Importing your frame...
        </p>
      </div>
      <div className="flex-1 w-full min-h-[200px] bg-sand-light rounded-2xl border border-stone/50 animate-pulse" />
    </div>
  );
}
