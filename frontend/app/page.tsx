"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { InterruptedScanDialog } from "@/components/interrupted-scan-dialog";
import { ScanProgressCard, ScanProgress } from "@/components/scan-progress";

interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
}

interface PlexStatus {
  connected: boolean;
  server_name: string | null;
}

interface ScanHistory {
  id: number;
  scan_type: string;
  status: string;
  total_items: number;
  processed_items: number;
  issues_found: number;
  started_at: string;
  completed_at?: string;
}

interface Issue {
  id: number;
  item_title: string;
  issue_type: string;
  status: string;
  created_at: string;
}

export default function HomePage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [plexStatus, setPlexStatus] = useState<PlexStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [pendingIssuesCount, setPendingIssuesCount] = useState(0);
  const [lastScan, setLastScan] = useState<ScanHistory | null>(null);
  const [recentIssues, setRecentIssues] = useState<Issue[]>([]);
  const [activeScan, setActiveScan] = useState<ScanProgress | null>(null);

  useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    try {
      // Check backend health
      const healthRes = await fetch("/api/health");
      if (healthRes.ok) {
        setHealth(await healthRes.json());
      }

      // Check Plex connection
      const plexRes = await fetch("/api/plex/status");
      if (plexRes.ok) {
        const status = await plexRes.json();
        setPlexStatus(status);

        // Only fetch additional data if connected
        if (status.connected) {
          await Promise.all([
            fetchPendingIssues(),
            fetchLastScan(),
            fetchRecentIssues(),
            checkActiveScan(),
          ]);
        }
      }
    } catch (error) {
      console.error("Failed to fetch status:", error);
    } finally {
      setLoading(false);
    }
  }

  async function fetchPendingIssues() {
    try {
      const res = await fetch("/api/issues?status=pending&limit=1");
      if (res.ok) {
        const data = await res.json();
        setPendingIssuesCount(data.total || 0);
      }
    } catch (error) {
      console.error("Failed to fetch pending issues:", error);
    }
  }

  async function fetchLastScan() {
    try {
      const res = await fetch("/api/scan/history?limit=1");
      if (res.ok) {
        const data = await res.json();
        if (data.scans && data.scans.length > 0) {
          setLastScan(data.scans[0]);
        }
      }
    } catch (error) {
      console.error("Failed to fetch scan history:", error);
    }
  }

  async function fetchRecentIssues() {
    try {
      const res = await fetch("/api/issues?limit=5");
      if (res.ok) {
        const data = await res.json();
        setRecentIssues(data.issues || []);
      }
    } catch (error) {
      console.error("Failed to fetch recent issues:", error);
    }
  }

  async function checkActiveScan() {
    try {
      const res = await fetch("/api/scan/status");
      if (res.ok) {
        const data = await res.json();
        if (data.status === "running" || data.status === "paused") {
          setActiveScan({
            scan_id: data.id,
            status: data.status,
            processed: data.processed_items,
            total: data.total_items,
            issues_found: data.issues_found,
            current_item: data.current_item,
            current_library: data.current_library,
          });
        }
      }
    } catch (error) {
      // No active scan
    }
  }

  async function handlePauseScan() {
    await fetch("/api/scan/pause", { method: "POST" });
    await checkActiveScan();
  }

  async function handleResumeScan() {
    await fetch("/api/scan/resume", { method: "POST" });
    await checkActiveScan();
  }

  async function handleCancelScan() {
    await fetch("/api/scan/cancel", { method: "POST" });
    setActiveScan(null);
  }

  function formatTimeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }

  function getIssueTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      NO_MATCH: "No Match",
      NO_POSTER: "Missing Poster",
      NO_BACKGROUND: "Missing Background",
      NO_LOGO: "Missing Logo",
      PLACEHOLDER_POSTER: "Placeholder Poster",
      PLACEHOLDER_BACKGROUND: "Placeholder Background",
    };
    return labels[type] || type;
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // If Plex is not connected, show onboarding prompt
  if (!plexStatus?.connected) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold mb-4">Welcome to MetaFix</h2>
          <p className="text-muted-foreground mb-8">
            A comprehensive Plex library management tool for artwork and edition metadata.
          </p>
        </div>

        <div className="bg-card border rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Get Started</h3>
          <p className="text-muted-foreground mb-4">
            To begin, you'll need to connect MetaFix to your Plex server.
          </p>
          <Link
            href="/onboarding"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Start Setup
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="bg-card border rounded-lg p-4">
            <h4 className="font-medium mb-2">Artwork Scanner</h4>
            <p className="text-sm text-muted-foreground">
              Detect missing posters, backgrounds, logos, and placeholder artwork across your entire library.
            </p>
          </div>
          <div className="bg-card border rounded-lg p-4">
            <h4 className="font-medium mb-2">Edition Manager</h4>
            <p className="text-sm text-muted-foreground">
              Automatically generate rich Edition metadata for movies based on technical information.
            </p>
          </div>
        </div>

        {health && (
          <div className="mt-8 text-center text-sm text-muted-foreground">
            Backend v{health.version} - {health.status}
          </div>
        )}
      </div>
    );
  }

  // Dashboard view when connected
  return (
    <div>
      {/* Interrupted scan dialog */}
      <InterruptedScanDialog onResolved={() => checkStatus()} />

      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold">Dashboard</h2>
          <p className="text-muted-foreground">
            Connected to: {plexStatus.server_name}
          </p>
        </div>
        <div className="flex space-x-2">
          <Link
            href="/scan"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            New Scan
          </Link>
        </div>
      </div>

      {/* Active scan card */}
      {activeScan && (
        <div className="mb-6">
          <ScanProgressCard
            progress={activeScan}
            onPause={handlePauseScan}
            onResume={handleResumeScan}
            onCancel={handleCancelScan}
          />
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3 mb-8">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Pending Issues
          </h3>
          <p className="text-3xl font-bold">{pendingIssuesCount}</p>
          {pendingIssuesCount > 0 && (
            <Link
              href="/issues"
              className="text-sm text-primary hover:underline mt-2 inline-block"
            >
              View all
            </Link>
          )}
        </div>
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Last Scan
          </h3>
          <p className="text-xl font-semibold">
            {lastScan ? formatTimeAgo(lastScan.started_at) : "Never"}
          </p>
          {lastScan && (
            <p className="text-sm text-muted-foreground mt-1">
              {lastScan.issues_found} issues found
            </p>
          )}
        </div>
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">
            Next Scheduled
          </h3>
          <p className="text-xl font-semibold">Not set</p>
          <Link
            href="/schedules"
            className="text-sm text-primary hover:underline mt-2 inline-block"
          >
            Configure
          </Link>
        </div>
      </div>

      <div className="bg-card border rounded-lg">
        <div className="p-4 border-b flex items-center justify-between">
          <h3 className="font-medium">Recent Issues</h3>
          {recentIssues.length > 0 && (
            <Link href="/issues" className="text-sm text-primary hover:underline">
              View all
            </Link>
          )}
        </div>
        {recentIssues.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            No issues found. Run a scan to detect problems.
          </div>
        ) : (
          <div className="divide-y">
            {recentIssues.map((issue) => (
              <div key={issue.id} className="p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{issue.item_title}</p>
                  <p className="text-sm text-muted-foreground">
                    {getIssueTypeLabel(issue.issue_type)}
                  </p>
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatTimeAgo(issue.created_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
