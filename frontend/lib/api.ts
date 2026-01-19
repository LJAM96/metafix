/**
 * API client for MetaFix backend
 */

const API_BASE = "/api";

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      return { error: error.detail || `Error: ${response.status}` };
    }

    const data = await response.json();
    return { data };
  } catch (error) {
    return { error: error instanceof Error ? error.message : "Network error" };
  }
}

// Health
export const api = {
  health: {
    check: () => request<{ status: string; version: string }>("/health"),
  },

  plex: {
    connect: (url: string, token: string) =>
      request<{ success: boolean; message: string; server_name?: string }>(
        "/plex/connect",
        {
          method: "POST",
          body: JSON.stringify({ url, token }),
        }
      ),
    status: () =>
      request<{ connected: boolean; server_name?: string; server_url?: string }>(
        "/plex/status"
      ),
    libraries: () =>
      request<{
        libraries: Array<{ id: string; name: string; type: string; item_count: number }>;
      }>("/plex/libraries"),
  },

  scan: {
    start: (config: object) =>
      request<{ scan_id: number; status: string; message: string }>("/scan/start", {
        method: "POST",
        body: JSON.stringify({ config }),
      }),
    status: () =>
      request<{
        id: number;
        scan_type: string;
        status: string;
        total_items: number;
        processed_items: number;
        issues_found: number;
        current_item?: string;
      }>("/scan/status"),
    pause: () => request<{ success: boolean }>("/scan/pause", { method: "POST" }),
    resume: () => request<{ success: boolean }>("/scan/resume", { method: "POST" }),
    cancel: () => request<{ success: boolean }>("/scan/cancel", { method: "POST" }),
    history: (limit?: number) =>
      request<{
        scans: Array<{
          id: number;
          scan_type: string;
          status: string;
          total_items: number;
          processed_items: number;
          issues_found: number;
          started_at: string;
          completed_at?: string;
        }>;
      }>(`/scan/history${limit ? `?limit=${limit}` : ""}`),
    interrupted: () =>
      request<{
        scan?: {
          id: number;
          scan_type: string;
          status: string;
          total_items: number;
          processed_items: number;
          issues_found: number;
          started_at: string;
          libraries: string[];
        };
      }>("/scan/interrupted"),
    discardInterrupted: () =>
      request<{ success: boolean }>("/scan/interrupted/discard", { method: "POST" }),
  },

  issues: {
    list: (params?: { page?: number; status?: string; type?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", params.page.toString());
      if (params?.status) searchParams.set("status", params.status);
      if (params?.type) searchParams.set("issue_type", params.type);
      return request<{
        total: number;
        page: number;
        issues: Array<object>;
      }>(`/issues?${searchParams}`);
    },
    accept: (issueId: number, suggestionId: number) =>
      request<{ success: boolean }>(`/issues/${issueId}/accept`, {
        method: "POST",
        body: JSON.stringify({ suggestion_id: suggestionId }),
      }),
    skip: (issueId: number) =>
      request<{ success: boolean }>(`/issues/${issueId}/skip`, { method: "POST" }),
  },

  edition: {
    modules: () =>
      request<{ modules: Array<{ name: string; description: string; example: string }> }>(
        "/edition/modules"
      ),
    config: () =>
      request<{
        enabled_modules: string[];
        module_order: string[];
        separator: string;
      }>("/edition/config"),
    updateConfig: (config: object) =>
      request<object>("/edition/config", {
        method: "PUT",
        body: JSON.stringify(config),
      }),
  },

  schedules: {
    list: () =>
      request<{ schedules: Array<object> }>("/schedules"),
    create: (schedule: object) =>
      request<object>("/schedules", {
        method: "POST",
        body: JSON.stringify(schedule),
      }),
    update: (id: number, schedule: object) =>
      request<object>(`/schedules/${id}`, {
        method: "PUT",
        body: JSON.stringify(schedule),
      }),
    delete: (id: number) =>
      request<{ success: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
    enable: (id: number) =>
      request<{ success: boolean }>(`/schedules/${id}/enable`, { method: "POST" }),
    disable: (id: number) =>
      request<{ success: boolean }>(`/schedules/${id}/disable`, { method: "POST" }),
    run: (id: number) =>
      request<{ success: boolean }>(`/schedules/${id}/run`, { method: "POST" }),
    presets: () =>
      request<{ presets: Array<{ name: string; cron: string }> }>("/schedules/presets"),
  },

  autofix: {
    start: (options?: { scan_id?: number; skip_unmatched?: boolean; min_score?: number }) =>
      request<{ success: boolean; message: string }>("/autofix/start", {
        method: "POST",
        body: JSON.stringify(options || {}),
      }),
    status: () =>
      request<{
        running: boolean;
        processed: number;
        total: number;
        applied: number;
        skipped: number;
        failed: number;
      }>("/autofix/status"),
    cancel: () => request<{ success: boolean }>("/autofix/cancel", { method: "POST" }),
  },

  settings: {
    providers: () => request<object>("/settings/providers"),
    updateProviders: (settings: object) =>
      request<{ success: boolean }>("/settings/providers", {
        method: "PUT",
        body: JSON.stringify(settings),
      }),
  },
};
