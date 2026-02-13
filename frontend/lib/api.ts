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
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
