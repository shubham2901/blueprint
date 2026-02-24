/**
 * Blueprint — API Client
 *
 * Fetch client + SSE event handling. All fetch calls include X-Request-Id for
 * request correlation. Use the request ID as the ref code for user-facing errors.
 */

import type {
  JourneyListResponse,
  JourneyDetailResponse,
  ResearchEvent,
  SelectionRequest,
  RefineRequest,
  CodeGenerateResponse,
  PrototypeSession,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// ──────────────────────────────────────────────────────
// Figma API
// ──────────────────────────────────────────────────────

export interface FigmaStatusResponse {
  connected: boolean;
}

export interface FigmaImportResponse {
  design_context: Record<string, unknown>;
  warnings: string[];
  thumbnail_url: string | null;
  frame_name: string | null;
  frame_width: number | null;
  frame_height: number | null;
  child_count: number;
  file_key?: string | null;
  node_id?: string | null;
}

/** Thrown when Figma API returns 429. Includes retry_after_seconds and upgrade_url when available. */
export class FigmaRateLimitError extends Error {
  constructor(
    message: string,
    public readonly retryAfterSeconds?: number,
    public readonly upgradeUrl?: string,
    public readonly errorCode?: string
  ) {
    super(message);
    this.name = "FigmaRateLimitError";
  }
}

/**
 * GET /api/figma/status — check if user has completed Figma OAuth.
 * Uses credentials: include for session cookie.
 */
export async function getFigmaStatus(): Promise<FigmaStatusResponse> {
  const requestId = generateRequestId();
  const res = await fetch(`${API_URL}/api/figma/status`, {
    method: "GET",
    credentials: "include",
    headers: { "X-Request-Id": requestId },
  });
  if (!res.ok) {
    return { connected: false };
  }
  return res.json() as Promise<FigmaStatusResponse>;
}

/**
 * POST /api/figma/disconnect — clear Figma OAuth tokens.
 * Call this before re-authenticating to ensure clean state.
 */
export async function disconnectFigma(): Promise<void> {
  const requestId = generateRequestId();
  await fetch(`${API_URL}/api/figma/disconnect`, {
    method: "POST",
    credentials: "include",
    headers: { "X-Request-Id": requestId },
  });
}

/**
 * POST /api/figma/import — import a Figma frame by URL.
 * Returns design_context and warnings. Throws with friendly message + (Ref: BP-XXX).
 */
export async function importFigmaFrame(url: string): Promise<FigmaImportResponse> {
  const requestId = generateRequestId();
  const res = await fetch(`${API_URL}/api/figma/import`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
    body: JSON.stringify({ url }),
  });
  const body = await res.json().catch(() => ({}));
  const detail = body?.detail ?? body;
  const errorCode = detail?.error_code || body?.error_code || requestId;
  const retryAfterSeconds = detail?.retry_after_seconds as number | undefined;
  const upgradeUrl = detail?.upgrade_url as string | undefined;
  if (res.status === 401) {
    // Auth error — need to reconnect
    const msg = detail?.message || "Connect with Figma to import this frame.";
    throw new Error(`${msg} (Ref: ${errorCode})`);
  }
  if (res.status === 400) {
    const msg = detail?.message || "That doesn't look like a valid Figma frame URL. Check the link and try again.";
    throw new Error(`${msg} (Ref: ${errorCode})`);
  }
  if (res.status === 403) {
    // Permission error — file is inaccessible (NOT an auth error)
    const msg = detail?.message || "We couldn't access that frame. It may be private or you may not have permission.";
    throw new Error(`${msg} (Ref: ${errorCode})`);
  }
  if (res.status === 429) {
    throw new FigmaRateLimitError(
      `Figma's API is rate limiting us. (Ref: ${errorCode})`,
      retryAfterSeconds,
      upgradeUrl,
      errorCode
    );
  }
  if (!res.ok) {
    throw new Error(`We couldn't import that frame. It may be private or the link may have expired. (Ref: ${errorCode})`);
  }
  return body as FigmaImportResponse;
}

// ──────────────────────────────────────────────────────
// Code Generation API
// ──────────────────────────────────────────────────────

/**
 * POST /api/code/generate — generate React code from Figma design context.
 * Blocks 10-30s until generation completes.
 * Throws with friendly message + (Ref: BP-XXX) on error.
 */
export async function generateCode(
  importResult: FigmaImportResponse
): Promise<CodeGenerateResponse> {
  const requestId = generateRequestId();
  const body = {
    design_context: importResult.design_context,
    thumbnail_url: importResult.thumbnail_url ?? undefined,
    frame_name: importResult.frame_name ?? undefined,
    frame_width: importResult.frame_width ?? undefined,
    frame_height: importResult.frame_height ?? undefined,
    file_key: importResult.file_key ?? undefined,
    node_id: importResult.node_id ?? undefined,
  };
  const res = await fetch(`${API_URL}/api/code/generate`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  const errorCode = data?.error_code || requestId;
  if (res.status === 401) {
    throw new Error(`Connect with Figma to generate code. (Ref: ${errorCode})`);
  }
  if (!res.ok) {
    throw new Error(
      `We're having trouble generating your prototype. Please try again. (Ref: ${errorCode})`
    );
  }
  return data as CodeGenerateResponse;
}

/**
 * GET /api/code/session — return current prototype session for bp_session cookie.
 * Returns null on 404 (no session).
 */
export async function getPrototypeSession(): Promise<PrototypeSession | null> {
  const requestId = generateRequestId();
  const res = await fetch(`${API_URL}/api/code/session`, {
    method: "GET",
    credentials: "include",
    headers: { "X-Request-Id": requestId },
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    return null;
  }
  return res.json() as Promise<PrototypeSession>;
}

function generateRequestId(): string {
  return `BP-${crypto.randomUUID().replace(/-/g, "").slice(0, 6).toUpperCase()}`;
}

export type EventCallback = (event: ResearchEvent) => void;
export type ErrorCallback = (error: Error) => void;
export type CompleteCallback = () => void;

export interface SSEConnection {
  close: () => void;
}

// ──────────────────────────────────────────────────────
// REST API
// ──────────────────────────────────────────────────────

/**
 * GET /api/journeys — list all journeys.
 * Throws with a user-facing ref code (BP-XXXXXX) on error.
 */
export async function getJourneys(): Promise<JourneyListResponse> {
  const requestId = generateRequestId();
  const res = await fetch(`${API_URL}/api/journeys`, {
    method: "GET",
    headers: {
      "X-Request-Id": requestId,
    },
  });
  if (!res.ok) {
    const msg = `Could not load journeys. (Ref: ${requestId})`;
    throw new Error(msg);
  }
  return res.json() as Promise<JourneyListResponse>;
}

/**
 * GET /api/journeys/{journeyId} — fetch a single journey.
 * Throws with a user-facing ref code (BP-XXXXXX) on error.
 */
export async function getJourney(journeyId: string): Promise<JourneyDetailResponse> {
  const requestId = generateRequestId();
  const res = await fetch(`${API_URL}/api/journeys/${encodeURIComponent(journeyId)}`, {
    method: "GET",
    headers: {
      "X-Request-Id": requestId,
    },
  });
  if (!res.ok) {
    const msg = `Could not load journey. (Ref: ${requestId})`;
    throw new Error(msg);
  }
  return res.json() as Promise<JourneyDetailResponse>;
}

// ──────────────────────────────────────────────────────
// SSE Parsing
// ──────────────────────────────────────────────────────

/**
 * Parses an SSE stream from a ReadableStream reader.
 * Handles partial chunks correctly by buffering until complete events (split on "\n\n").
 * For each line starting with "data: ", strips prefix, JSON.parses, and calls onEvent.
 * Calls onComplete when reader.done, onError on stream/parse errors.
 */
function parseSSEStream(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback
): void {
  const decoder = new TextDecoder();
  let buffer = "";

  async function pump(): Promise<void> {
    try {
      const { done, value } = await reader.read();
      if (done) {
        onComplete();
        return;
      }
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";
      for (const eventBlock of events) {
        const lines = eventBlock.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr === "") continue;
            try {
              const event = JSON.parse(jsonStr) as ResearchEvent;
              onEvent(event);
            } catch {
              onError(new Error(`Invalid SSE JSON: ${jsonStr.slice(0, 100)}`));
            }
          }
        }
      }
      await pump();
    } catch (err) {
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  }
  pump();
}

// ──────────────────────────────────────────────────────
// SSE Research API
// ──────────────────────────────────────────────────────

/**
 * POST /api/research — start research with prompt.
 * Streams SSE events via onEvent. Uses AbortController for cancellation.
 * Returns SSEConnection with close() to abort.
 * Calls onError for non-200 responses before stream starts, or stream/parse errors.
 */
export function startResearch(
  prompt: string,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback
): SSEConnection {
  const controller = new AbortController();
  const requestId = generateRequestId();

  fetch(`${API_URL}/api/research`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
    body: JSON.stringify({ prompt }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const msg = `Could not start research. (Ref: ${requestId})`;
        onError(new Error(msg));
        return;
      }
      const body = res.body;
      if (!body) {
        onComplete();
        return;
      }
      parseSSEStream(
        body.getReader(),
        onEvent,
        (err) => onError(err),
        onComplete
      );
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
    });

  return {
    close: () => controller.abort(),
  };
}

/**
 * POST /api/research/{journeyId}/selection — send user selection.
 * Streams SSE events via onEvent. Uses AbortController for cancellation.
 * Returns SSEConnection with close() to abort.
 * Calls onError for non-200 responses before stream starts, or stream/parse errors.
 */
export function sendSelection(
  journeyId: string,
  selection: SelectionRequest,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback
): SSEConnection {
  const controller = new AbortController();
  const requestId = generateRequestId();

  fetch(`${API_URL}/api/research/${encodeURIComponent(journeyId)}/selection`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
    body: JSON.stringify(selection),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const msg = `Could not send selection. (Ref: ${requestId})`;
        onError(new Error(msg));
        return;
      }
      const body = res.body;
      if (!body) {
        onComplete();
        return;
      }
      parseSSEStream(
        body.getReader(),
        onEvent,
        (err) => onError(err),
        onComplete
      );
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
    });

  return {
    close: () => controller.abort(),
  };
}

/**
 * POST /api/research/{journeyId}/refine — refine a research step.
 * Streams SSE events via onEvent. Uses AbortController for cancellation.
 * Returns SSEConnection with close() to abort.
 * Calls onError for non-200 responses before stream starts, or stream/parse errors.
 */
export function sendRefine(
  journeyId: string,
  request: RefineRequest,
  onEvent: EventCallback,
  onError: ErrorCallback,
  onComplete: CompleteCallback
): SSEConnection {
  const controller = new AbortController();
  const requestId = generateRequestId();

  fetch(`${API_URL}/api/research/${encodeURIComponent(journeyId)}/refine`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Request-Id": requestId,
    },
    body: JSON.stringify(request),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const msg = `Could not refine research. (Ref: ${requestId})`;
        onError(new Error(msg));
        return;
      }
      const body = res.body;
      if (!body) {
        onComplete();
        return;
      }
      parseSSEStream(
        body.getReader(),
        onEvent,
        (err) => onError(err),
        onComplete
      );
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
    });

  return {
    close: () => controller.abort(),
  };
}
