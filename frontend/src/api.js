/**
 * =============================================================================
 * Project: Explainable Multilingual Legal Meaning Preservation Using JUDGEBERT
 * File: frontend/src/api.js
 * Task: Lightweight API Client for JUDGEBERT Flask Backend
 * =============================================================================
 *
 * Communicates with the Flask REST API via the Vite development proxy (/api).
 */

/**
 * Evaluates an original statutory text and simplified candidate text pair.
 * Calls POST /api/evaluate-pair which runs neural inference and explainability
 * in a single execution pass.
 *
 * @param {Object} params
 * @param {string} params.originalText - Statutory source passage
 * @param {string} params.simplifiedText - Plain-language candidate text
 * @param {string} [params.language='en'] - 'en' or 'hi'
 * @returns {Promise<Object>} API response with prediction, explanation, and latency
 */
export async function evaluateTextPair({ originalText, simplifiedText, language = 'en' }) {
  // Client-side validation prior to network dispatch
  const trimmedOrig = (originalText || '').trim();
  const trimmedSimp = (simplifiedText || '').trim();

  if (!trimmedOrig) {
    throw new Error('Please enter the Original Legal Text.');
  }
  if (!trimmedSimp) {
    throw new Error('Please enter the Simplified Legal Text.');
  }

  const payload = {
    original_text: trimmedOrig,
    simplified_text: trimmedSimp,
    language: language,
  };

  const startTime = performance.now();
  let response;

  try {
    response = await fetch('/api/evaluate-pair', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (networkError) {
    // Graceful offline / connection failure handling
    throw new Error(
      'Unable to connect to the JUDGEBERT backend service. Please ensure the Flask server is active on http://127.0.0.1:5000.'
    );
  }

  const clientLatencyMs = Math.round(performance.now() - startTime);

  let data;
  try {
    data = await response.json();
  } catch (parseError) {
    throw new Error(
      `Received invalid response from server (HTTP ${response.status}).`
    );
  }

  if (!response.ok || !data.success) {
    const message =
      data?.message ||
      data?.error ||
      `Evaluation request failed with HTTP ${response.status}.`;
    throw new Error(message);
  }

  return {
    ...data,
    client_latency_ms: clientLatencyMs,
  };
}

/**
 * Checks system health and model readiness status.
 * Calls GET /api/health
 *
 * @returns {Promise<Object>} Health status payload
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch('/api/health');
    if (!response.ok) {
      return { status: 'unhealthy', model_loaded: false };
    }
    return await response.json();
  } catch {
    return { status: 'unavailable', model_loaded: false };
  }
}
