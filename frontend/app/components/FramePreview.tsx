"use client";

import { useState } from "react";

interface FramePreviewProps {
  thumbnailUrl: string | null;
  frameName: string | null;
  frameWidth: number | null;
  frameHeight: number | null;
  childCount: number;
  warnings: string[];
  onImportAnother: () => void;
  onRegenerate?: () => void;
}

export function FramePreview({
  thumbnailUrl,
  frameName,
  frameWidth,
  frameHeight,
  childCount,
  warnings,
  onImportAnother,
  onRegenerate,
}: FramePreviewProps) {
  const [imgLoaded, setImgLoaded] = useState(false);

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-green-500" />
            <h2 className="font-serif text-xl text-charcoal">
              {frameName || "Frame imported"}
            </h2>
          </div>
          <div className="flex items-center gap-3 text-xs text-charcoal-light ml-4">
            {frameWidth && frameHeight && (
              <span>{frameWidth} × {frameHeight}px</span>
            )}
            {childCount > 0 && (
              <>
                <span className="text-stone">·</span>
                <span>{childCount} layer{childCount !== 1 ? "s" : ""}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              className="text-xs text-charcoal-light hover:text-charcoal hover:underline transition-colors"
            >
              Regenerate
            </button>
          )}
          <button
            type="button"
            onClick={onImportAnother}
            className="text-xs text-charcoal-light hover:text-charcoal hover:underline transition-colors"
          >
            Import another frame
          </button>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="mb-4 px-4 py-2.5 bg-amber-50 border border-amber-200 rounded-xl">
          <p className="text-xs text-amber-800 font-medium mb-1">Heads up</p>
          {warnings.map((w) => (
            <p key={w} className="text-xs text-amber-700">{w}</p>
          ))}
        </div>
      )}

      {/* Frame thumbnail */}
      <div className="w-full bg-sand-light rounded-2xl border border-stone/50 overflow-hidden flex items-center justify-center">
        {thumbnailUrl ? (
          <div className="relative w-full flex items-center justify-center p-6">
            {!imgLoaded && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="animate-pulse bg-stone/30 rounded-xl w-3/4 h-3/4" />
              </div>
            )}
            <img
              src={thumbnailUrl}
              alt={frameName || "Imported Figma frame"}
              className={`max-w-full object-contain rounded-lg shadow-sm transition-opacity duration-300 ${imgLoaded ? "opacity-100" : "opacity-0"}`}
              onLoad={() => setImgLoaded(true)}
            />
          </div>
        ) : (
          <div className="text-center p-8">
            <div className="w-16 h-16 bg-stone/20 rounded-2xl flex items-center justify-center mx-auto mb-3">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-charcoal-light">
                <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" strokeWidth="1.5" />
                <path d="M3 16l5-5 4 4 3-3 6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="text-sm text-charcoal-light">Frame imported successfully</p>
            <p className="text-xs text-charcoal-light/60 mt-1">Thumbnail unavailable</p>
          </div>
        )}
      </div>

      {/* Success message */}
      <div className="mt-4 text-center">
        <p className="text-xs text-charcoal-light">
          Your prototype is ready
        </p>
      </div>
    </div>
  );
}
