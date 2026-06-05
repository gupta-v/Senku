#pragma once
#include <Arduino.h>

// ── Thread management ────────────────────────────────────────

/**
 * POST /senku/create-thread → {"thread_id": "..."}
 * Returns true and populates outThreadId on success.
 */
bool createThread(String& outThreadId);

/**
 * POST /senku/respond-stream with {query, thread_id}.
 * Reads the SSE stream and calls appendToken() for each token.
 * Returns true when "[DONE]" is received, false on error/timeout.
 */
bool streamRespond(const String& query, const String& threadId);

/**
 * GET /senku/health — returns true if the server is ready.
 */
bool checkServerHealth();
