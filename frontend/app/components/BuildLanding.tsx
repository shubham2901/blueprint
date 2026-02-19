"use client";

/**
 * Build Landing — Connect CTA and intro
 *
 * Shown when user hasn't pasted a URL. Connect with Figma button;
 * onConnectClick wired to OAuth in 01-05.
 */

interface BuildLandingProps {
  onConnectClick: () => void;
  onPasteUrlClick: () => void;
}

export function BuildLanding({ onConnectClick, onPasteUrlClick }: BuildLandingProps) {
  return (
    <div className="text-center max-w-lg mx-auto flex flex-col items-center">
      <h1 className="font-serif text-5xl text-charcoal mb-4 italic leading-tight">
        Turn your Figma into a working prototype
      </h1>
      <p className="text-charcoal-light font-normal text-lg tracking-wide max-w-md mx-auto mb-10">
        Import a frame, describe what you want in chat, get live Prototype.
      </p>
      <div className="flex flex-col items-center gap-4">
        <button
          type="button"
          onClick={onConnectClick}
          className="bg-terracotta hover:bg-primary-dark text-white px-6 py-3 rounded-lg text-sm font-medium transition-colors shadow-sm"
        >
          Connect with Figma
        </button>
        <button
          type="button"
          onClick={onPasteUrlClick}
          className="text-charcoal-light text-sm hover:text-charcoal hover:underline transition-colors"
        >
          Paste frame URL instead
        </button>
        <a
          href="#"
          className="text-charcoal-light text-sm hover:text-charcoal hover:underline transition-colors"
        >
          How it works
        </a>
      </div>
    </div>
  );
}
