"use client";

/**
 * Paste URL View — Figma frame URL input + Import
 *
 * Connect-vs-paste: if figmaConnected is false and user has pasted URL,
 * show "Connect with Figma to import this frame." Import disabled until connected.
 */

interface PasteUrlViewProps {
  figmaUrl: string;
  onUrlChange: (url: string) => void;
  onImportClick: () => void;
  figmaConnected: boolean;
  onConnectClick: () => void;
  onBackClick: () => void;
}

export function PasteUrlView({
  figmaUrl,
  onUrlChange,
  onImportClick,
  figmaConnected,
  onConnectClick,
  onBackClick,
}: PasteUrlViewProps) {
  const hasUrl = figmaUrl.trim().length > 0;
  const showConnectPrompt = hasUrl && !figmaConnected;
  const canImport = hasUrl && figmaConnected;

  return (
    <div className="w-full max-w-xl mx-auto flex flex-col">
      <button
        type="button"
        onClick={onBackClick}
        className="text-charcoal-light text-sm hover:text-charcoal mb-6 self-start"
      >
        ← Back
      </button>
      <h1 className="font-serif text-3xl font-bold text-charcoal mb-8 text-center">
        Paste your Figma frame URL to get started.
      </h1>
      <div className="w-full">
        <label
          className="block text-xs font-semibold text-charcoal-light uppercase tracking-wider mb-2 ml-1"
          htmlFor="figma-url"
        >
          Figma frame URL
        </label>
        <div className="flex items-center gap-2">
          <input
            id="figma-url"
            type="text"
            value={figmaUrl}
            onChange={(e) => onUrlChange(e.target.value)}
            placeholder="https://figma.com/design/..."
            className="flex-1 w-full bg-sand-light border border-stone rounded-xl px-4 py-3 text-sm text-charcoal placeholder-charcoal-light/50 focus:ring-2 focus:ring-terracotta/20 focus:border-terracotta outline-none transition-all"
          />
          <button
            type="button"
            onClick={canImport ? onImportClick : showConnectPrompt ? onConnectClick : undefined}
            disabled={!hasUrl}
            className="bg-terracotta hover:bg-primary-dark text-white px-8 py-3 rounded-xl text-sm font-semibold transition-all shadow-sm active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            Import
          </button>
        </div>
        {figmaConnected && (
          <div className="mt-3 flex items-center gap-2 text-xs text-charcoal-light">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Connected to Figma
          </div>
        )}
        {showConnectPrompt && (
          <p className="mt-4 text-sm text-charcoal-light">
            Connect with Figma to import this frame.
          </p>
        )}
        <p className="mt-4 text-center text-charcoal-light text-xs">
          Need help?{" "}
          <a
            href="https://help.figma.com/hc/en-us/articles/360039832654-Share-a-design-file#Share_a_specific_frame"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-charcoal"
          >
            Learn how to find your frame URL
          </a>
        </p>
      </div>
    </div>
  );
}
