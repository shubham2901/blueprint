"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BuildLanding } from "@/app/components/BuildLanding";
import { PasteUrlView } from "@/app/components/PasteUrlView";
import { ImportingView } from "@/app/components/ImportingView";
import { getFigmaStatus, importFigmaFrame } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Build Shell — Phase 1
 *
 * Cursor-like layout: main ~65%, sidebar ~35%.
 * Tabs: Research | Blueprint | Build (Build active).
 * Main area: BuildLanding | PasteUrlView | ImportingView | success/error.
 */

type ViewMode = "landing" | "paste" | "importing" | "success" | "error";

function BuildShellContent() {
  const searchParams = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>("landing");
  const [figmaUrl, setFigmaUrl] = useState("");
  const [figmaConnected, setFigmaConnected] = useState(false);
  const [designContext, setDesignContext] = useState<Record<string, unknown> | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // OAuth return: ?figma_connected=1 or ?figma_error=1&error_code=BP-XXX
  useEffect(() => {
    const connected = searchParams.get("figma_connected");
    const error = searchParams.get("figma_error");
    const errorCode = searchParams.get("error_code");
    if (connected === "1") {
      setFigmaConnected(true);
      window.history.replaceState(null, "", "/");
    }
    if (error === "1" && errorCode) {
      setImportError(`We couldn't connect to Figma. Please try again. (Ref: ${errorCode})`);
      window.history.replaceState(null, "", "/");
    }
  }, [searchParams]);

  // Check Figma status on mount (handles refresh)
  useEffect(() => {
    getFigmaStatus().then((res) => setFigmaConnected(res.connected));
  }, []);

  const handleConnectClick = () => {
    window.location.href = `${API_URL}/api/figma/oauth/start`;
  };

  const handleImportClick = async () => {
    if (!figmaUrl.trim() || !figmaConnected) return;
    setViewMode("importing");
    setImportError(null);
    try {
      const res = await importFigmaFrame(figmaUrl.trim());
      setDesignContext(res.design_context);
      setViewMode("success");
    } catch (e) {
      setImportError(e instanceof Error ? e.message : "Something went wrong. Please try again.");
      setViewMode("error");
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-sand-light p-3 gap-3">
      {/* Main area (~65%) */}
      <main className="flex-1 flex flex-col bg-white rounded-3xl border border-stone shadow-sm overflow-hidden min-w-0">
        <header className="h-16 flex items-end px-12 border-b border-stone shrink-0">
          <div className="flex space-x-8 h-full w-full items-end">
            <Link
              href="/research"
              className="relative pb-4 flex items-center text-sm font-medium text-charcoal-light hover:text-charcoal transition-colors px-1"
            >
              Research
            </Link>
            <Link
              href="/research"
              className="relative pb-4 flex items-center text-sm font-medium text-charcoal-light hover:text-charcoal transition-colors px-1"
            >
              Blueprint
            </Link>
            <button
              type="button"
              className="relative pb-4 flex items-center text-base font-serif italic text-charcoal px-1 cursor-default"
            >
              Build
              <div className="absolute bottom-[-1px] left-0 w-full h-[3px] bg-charcoal rounded-t-full" />
            </button>
          </div>
        </header>
        <div className="flex-1 flex items-center justify-center p-12 min-h-0 overflow-auto">
          {viewMode === "landing" && (
            <BuildLanding
              onConnectClick={handleConnectClick}
              onPasteUrlClick={() => setViewMode("paste")}
            />
          )}
          {viewMode === "paste" && (
            <PasteUrlView
              figmaUrl={figmaUrl}
              onUrlChange={setFigmaUrl}
              onImportClick={handleImportClick}
              figmaConnected={figmaConnected}
              onConnectClick={handleConnectClick}
              onBackClick={() => setViewMode("landing")}
            />
          )}
          {viewMode === "importing" && <ImportingView figmaUrl={figmaUrl} />}
          {viewMode === "success" && (
            <div className="text-center max-w-lg mx-auto">
              <h2 className="font-serif text-2xl text-charcoal mb-4">Frame imported</h2>
              <p className="text-charcoal-light text-sm mb-6">
                Design context loaded. Code generation coming in Phase 2.
              </p>
              <button
                type="button"
                onClick={() => {
                  setViewMode("paste");
                  setDesignContext(null);
                }}
                className="text-charcoal-light text-sm hover:text-charcoal hover:underline"
              >
                Import another frame
              </button>
            </div>
          )}
          {viewMode === "error" && (
            <div className="text-center max-w-lg mx-auto">
              <p className="text-charcoal mb-4">{importError}</p>
              <button
                type="button"
                onClick={() => {
                  setViewMode("paste");
                  setImportError(null);
                }}
                className="text-terracotta hover:underline text-sm"
              >
                Try again
              </button>
            </div>
          )}
          {importError && viewMode !== "error" && (
            <div className="fixed top-4 right-4 bg-white border border-stone rounded-lg shadow-lg px-4 py-3 text-sm text-charcoal max-w-md">
              {importError}
            </div>
          )}
        </div>
      </main>

      {/* Sidebar (~35%) */}
      <aside className="w-[35%] min-w-[400px] max-w-[550px] bg-sand-dark rounded-2xl border border-stone flex flex-col h-full shadow-sm overflow-hidden shrink-0">
        <header className="h-20 flex items-center justify-between px-6 shrink-0 bg-sand-dark/50 backdrop-blur-sm border-b border-stone/30">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-charcoal rounded-lg flex items-center justify-center shadow-md">
              <span className="font-serif italic text-sand-light text-sm font-bold">
                B
              </span>
            </div>
            <h2 className="font-serif font-medium text-charcoal text-lg tracking-tight">
              Blueprint
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 bg-white/60 px-3 py-1.5 rounded-full border border-stone/40">
              <span className="w-1.5 h-1.5 rounded-full bg-terracotta animate-pulse" />
              <span className="text-[10px] font-semibold text-charcoal-light whitespace-nowrap uppercase tracking-wider">
                1 session left
              </span>
            </div>
            <button
              type="button"
              className="text-xs font-semibold px-4 py-1.5 bg-white border border-stone text-charcoal hover:bg-stone/20 transition-all rounded-full shadow-sm"
            >
              Sign up
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto px-6 py-4 flex flex-col">
          <div className="mt-8 space-y-6">
            <h1 className="text-3xl font-serif italic text-charcoal leading-tight">
              What are you building today?
            </h1>
          </div>
          <div className="flex-1" />
        </div>
        <div className="mt-auto px-6 pb-6 pt-2 shrink-0">
          <div className="relative bg-white rounded-2xl shadow-sm border border-stone focus-within:border-terracotta/40 focus-within:shadow-md transition-all duration-300 p-4">
            <textarea
              placeholder="Ask me to build something..."
              rows={2}
              className="w-full bg-transparent border-none p-0 text-sm text-charcoal placeholder-charcoal-light/60 focus:ring-0 resize-none font-sans leading-relaxed"
              disabled
            />
            <div className="flex justify-end items-center mt-2">
              <button
                type="button"
                disabled
                className="flex items-center gap-2 px-6 py-2.5 bg-charcoal hover:bg-primary-dark rounded-xl text-sand-light transition-all shadow-md opacity-60 cursor-not-allowed"
              >
                <span className="text-xs font-bold tracking-widest">RUN</span>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}

export default function BuildShellPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-sand-light">Loading...</div>}>
      <BuildShellContent />
    </Suspense>
  );
}
