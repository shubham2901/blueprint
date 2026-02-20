"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { BuildLanding } from "@/app/components/BuildLanding";
import { PasteUrlView } from "@/app/components/PasteUrlView";
import { ImportingView } from "@/app/components/ImportingView";
import { FramePreview } from "@/app/components/FramePreview";
import { GeneratingView } from "@/app/components/GeneratingView";
import {
  getFigmaStatus,
  importFigmaFrame,
  generateCode,
  getPrototypeSession,
  type FigmaImportResponse,
} from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Build Shell — Phase 1
 *
 * Cursor-like layout: main ~65%, sidebar ~35%.
 * Tabs: Research | Blueprint | Build (Build active).
 * Main area: BuildLanding | PasteUrlView | ImportingView | success/error.
 */

type ViewMode = "landing" | "paste" | "importing" | "generating" | "success" | "error";

function BuildShellContent() {
  const searchParams = useSearchParams();
  const [viewMode, setViewMode] = useState<ViewMode>("landing");
  const [figmaUrl, setFigmaUrl] = useState("");
  const [figmaConnected, setFigmaConnected] = useState(false);
  const [importResult, setImportResult] = useState<FigmaImportResponse | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const markFigmaConnected = (connected: boolean) => {
    setFigmaConnected(connected);
    if (connected) {
      localStorage.setItem("bp_figma_connected", "1");
    } else {
      localStorage.removeItem("bp_figma_connected");
    }
  };

  // OAuth return: ?figma_connected=1 or ?figma_error=1&error_code=BP-XXX
  useEffect(() => {
    const connected = searchParams.get("figma_connected");
    const error = searchParams.get("figma_error");
    const errorCode = searchParams.get("error_code");
    if (connected === "1") {
      markFigmaConnected(true);
      setViewMode("paste");
      const savedUrl = localStorage.getItem("bp_figma_url");
      if (savedUrl) {
        setFigmaUrl(savedUrl);
        localStorage.removeItem("bp_figma_url");
      }
      window.history.replaceState(null, "", "/");
    }
    if (error === "1" && errorCode) {
      setImportError(`We couldn't connect to Figma. Please try again. (Ref: ${errorCode})`);
      setViewMode("paste");
      const savedUrl = localStorage.getItem("bp_figma_url");
      if (savedUrl) {
        setFigmaUrl(savedUrl);
        localStorage.removeItem("bp_figma_url");
      }
      window.history.replaceState(null, "", "/");
    }
  }, [searchParams]);

  // Restore from localStorage, then verify with backend
  useEffect(() => {
    const stored = localStorage.getItem("bp_figma_connected") === "1";
    if (stored) setFigmaConnected(true);

    getFigmaStatus().then((res) => {
      if (res.connected) {
        markFigmaConnected(true);
      } else if (stored) {
        markFigmaConnected(false);
      }
    });
  }, []);

  // Session restore on mount: if we have a ready prototype session, show success
  useEffect(() => {
    getPrototypeSession().then((session) => {
      if (session?.status === "ready") {
        setSessionId(session.session_id);
        setImportResult({
          design_context: session.design_context ?? {},
          thumbnail_url: session.thumbnail_url ?? null,
          frame_name: session.frame_name ?? null,
          frame_width: session.frame_width ?? null,
          frame_height: session.frame_height ?? null,
          child_count: 0,
          warnings: [],
          file_key: undefined,
          node_id: undefined,
        });
        setViewMode("success");
      }
    });
  }, []);

  const handleConnectClick = () => {
    if (figmaConnected) {
      setViewMode("paste");
      return;
    }
    if (figmaUrl.trim()) {
      localStorage.setItem("bp_figma_url", figmaUrl.trim());
    }
    window.location.href = `${API_URL}/api/figma/oauth/start`;
  };

  const handleImportClick = async () => {
    if (!figmaUrl.trim() || !figmaConnected) return;
    setViewMode("importing");
    setImportError(null);
    try {
      const res = await importFigmaFrame(figmaUrl.trim());
      setImportResult(res);
      setViewMode("generating");
      try {
        const codeRes = await generateCode(res);
        if (codeRes.status === "ready") {
          setSessionId(codeRes.session_id);
          setViewMode("success");
        } else {
          setImportError(
            `We're having trouble generating your prototype. Please try again. (Ref: ${codeRes.error_code || "BP-XXXXXX"})`
          );
          setViewMode("error");
        }
      } catch (genErr) {
        const msg =
          genErr instanceof Error
            ? genErr.message
            : "We're having trouble generating your prototype. Please try again.";
        if (msg.includes("Connect with Figma")) {
          markFigmaConnected(false);
        }
        setImportError(msg);
        setViewMode("error");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Please try again.";
      if (msg.includes("Connect with Figma")) {
        markFigmaConnected(false);
      }
      setImportError(msg);
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
              className="relative pb-4 flex items-center text-base font-serif font-bold text-charcoal px-1 cursor-default"
            >
              Build
              <div className="absolute bottom-[-1px] left-0 w-full h-[3px] bg-charcoal rounded-t-full" />
            </button>
          </div>
        </header>
        <div className="flex-1 flex items-start justify-center p-12 min-h-0 overflow-auto">
          {viewMode === "landing" && (
            <BuildLanding
              onConnectClick={handleConnectClick}
              onPasteUrlClick={() => setViewMode("paste")}
              figmaConnected={figmaConnected}
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
          {viewMode === "generating" && <GeneratingView />}
          {viewMode === "success" && importResult && (
            <FramePreview
              thumbnailUrl={importResult.thumbnail_url}
              frameName={importResult.frame_name}
              frameWidth={importResult.frame_width}
              frameHeight={importResult.frame_height}
              childCount={importResult.child_count}
              warnings={importResult.warnings}
              onImportAnother={() => {
                setViewMode("paste");
                setImportResult(null);
              }}
            />
          )}
          {viewMode === "error" && (
            <div className="text-center max-w-lg mx-auto">
              <p className="text-charcoal mb-4">{importError}</p>
              <button
                type="button"
                onClick={async () => {
                  if (importResult) {
                    setViewMode("generating");
                    setImportError(null);
                    try {
                      const codeRes = await generateCode(importResult);
                      if (codeRes.status === "ready") {
                        setSessionId(codeRes.session_id);
                        setViewMode("success");
                      } else {
                        setImportError(
                          `We're having trouble generating your prototype. Please try again. (Ref: ${codeRes.error_code || "BP-XXXXXX"})`
                        );
                        setViewMode("error");
                      }
                    } catch (genErr) {
                      setImportError(
                        genErr instanceof Error
                          ? genErr.message
                          : "We're having trouble generating your prototype. Please try again."
                      );
                      setViewMode("error");
                    }
                  } else {
                    setViewMode("paste");
                    setImportError(null);
                  }
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
              <span className="font-serif text-sand-light text-sm font-bold">
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
            <h1 className="text-3xl font-serif font-bold text-charcoal leading-tight">
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
