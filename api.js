/**
 * NEXUS API client
 *
 * Production rule:
 * - Never invent operational data.
 * - Never use Math.random().
 * - The browser reads only from /api/*.
 * - If a backend/integration is unavailable, the UI receives data: null
 *   and renders an explicit NOT CONNECTED / NO DATA state.
 */

const NEXUS_API_BASE = "/api";

async function nexusFetch(path) {
  try {
    const response = await fetch(`${NEXUS_API_BASE}${path}`, {
      headers: { "Accept": "application/json" },
    });

    if (!response.ok) {
      return {
        mode: "error",
        source: "NEXUS API",
        data: null,
        error: `HTTP ${response.status}`,
      };
    }

    const json = await response.json();

    return {
      mode: json.mode || "live",
      source: json.source || "NEXUS API",
      updatedAt: json.updatedAt || new Date().toISOString(),
      data: json.data ?? null,
      error: json.error || null,
    };
  } catch (error) {
    return {
      mode: "unavailable",
      source: "NEXUS API",
      data: null,
      error: String(error),
    };
  }
}

/**
 * Kick off a deploy. `apiKey` is optional — only required if the backend
 * has NEXUS_API_KEY set. Returns the normalized {mode, data: {jobId}} shape.
 */
async function nexusDeployUpload(file, appName, apiKey) {
  const formData = new FormData();
  formData.append("file", file);
  if (appName) formData.append("app_name", appName);

  try {
    const headers = {};
    if (apiKey) headers["X-Nexus-Api-Key"] = apiKey;

    const res = await fetch(`${NEXUS_API_BASE}/deploy`, {
      method: "POST",
      headers,
      body: formData,
    });

    const json = await res.json().catch(() => ({}));

    if (!res.ok) {
      const msg = res.status === 404
        ? "No NEXUS backend found at /api/deploy. If you're viewing this as a published preview, run the real backend locally (`docker-compose up`) and open it at its own URL instead."
        : (json.detail || `HTTP ${res.status}`);
      return { mode: "error", data: null, error: msg };
    }

    return { mode: json.mode || "live", data: json.data ?? null, error: json.error || null };
  } catch (error) {
    return {
      mode: "unavailable",
      data: null,
      error: "Couldn't reach the NEXUS backend at all. Is it running, and is this page being served from it?",
    };
  }
}

/**
 * Opens a live event stream for one job's progress/logs. Calls `onUpdate`
 * with the job detail payload each time something changes, and `onDone`
 * once the job reaches a terminal state (or the stream errors out).
 */
function nexusStreamDeployJob(jobId, onUpdate, onDone) {
  const source = new EventSource(`${NEXUS_API_BASE}/deploy/jobs/${jobId}/stream`);

  source.onmessage = (event) => {
    try {
      const detail = JSON.parse(event.data);
      onUpdate(detail);
      if (detail.status === "success" || detail.status === "failed") {
        source.close();
        onDone && onDone(detail);
      }
    } catch (err) {
      // ignore malformed frames
    }
  };

  source.onerror = () => {
    source.close();
    onDone && onDone(null);
  };

  return source;
}

const NexusAPI = {
  getHealth: () => nexusFetch("/health"),
  getDeployments: () => nexusFetch("/deployments"),
  getPipelineRun: () => nexusFetch("/pipelines"),
  getKubernetes: () => nexusFetch("/kubernetes"),
  getObservability: () => nexusFetch("/observability"),
  getLogs: () => nexusFetch("/logs"),
  getGitOps: () => nexusFetch("/gitops"),
  getSecurity: () => nexusFetch("/security"),
  getInfrastructure: () => nexusFetch("/infrastructure"),
  getCosts: () => nexusFetch("/costs"),
  getPlatformMetrics: () => nexusFetch("/metrics"),

  deployUpload: nexusDeployUpload,
  streamDeployJob: nexusStreamDeployJob,
  getDeployConfig: () => nexusFetch("/deploy/config"),
  getDeployJobs: () => nexusFetch("/deploy/jobs"),
  getDeployJob: (id) => nexusFetch(`/deploy/jobs/${id}`),
};
