"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ScanStatusBadge } from "@/components/scan-progress";

interface ScanRecord {
  id: number;
  scan_type: string;
  status: string;
  total_items: number;
  processed_items: number;
  issues_found: number;
  started_at: string;
  completed_at?: string;
  libraries?: string[];
}

export default function ScanHistoryPage() {
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, [page]);

  async function fetchHistory() {
    setLoading(true);
    try {
      const res = await fetch(`/api/scan/history?page=${page}&limit=20`);
      if (res.ok) {
        const data = await res.json();
        setScans(data.scans || []);
        setHasMore(data.has_more || false);
      }
    } catch (error) {
      console.error("Failed to fetch scan history:", error);
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatDuration(startedAt: string, completedAt?: string): string {
    if (!completedAt) return "-";
    const start = new Date(startedAt);
    const end = new Date(completedAt);
    const diffMs = end.getTime() - start.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const mins = Math.floor(diffSecs / 60);
    const secs = diffSecs % 60;

    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  }

  function getScanTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      artwork: "Artwork Scan",
      edition: "Edition Scan",
      both: "Full Scan",
    };
    return labels[type] || type;
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Scan History</h1>
          <p className="text-muted-foreground">
            View past scans and their results
          </p>
        </div>
        <Link
          href="/scan"
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          New Scan
        </Link>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      ) : scans.length === 0 ? (
        <div className="bg-card border rounded-lg p-12 text-center">
          <p className="text-muted-foreground mb-4">No scan history found.</p>
          <Link
            href="/scan"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Start your first scan
          </Link>
        </div>
      ) : (
        <>
          <div className="bg-card border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-4 font-medium">Date</th>
                  <th className="text-left p-4 font-medium">Type</th>
                  <th className="text-left p-4 font-medium">Status</th>
                  <th className="text-right p-4 font-medium">Items</th>
                  <th className="text-right p-4 font-medium">Issues</th>
                  <th className="text-right p-4 font-medium">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {scans.map((scan) => (
                  <tr key={scan.id} className="hover:bg-muted/30">
                    <td className="p-4">
                      <div className="font-medium">
                        {formatDate(scan.started_at)}
                      </div>
                      {scan.libraries && scan.libraries.length > 0 && (
                        <div className="text-sm text-muted-foreground">
                          {scan.libraries.join(", ")}
                        </div>
                      )}
                    </td>
                    <td className="p-4">
                      <span className="text-sm">
                        {getScanTypeLabel(scan.scan_type)}
                      </span>
                    </td>
                    <td className="p-4">
                      <ScanStatusBadge
                        status={
                          scan.status as
                            | "pending"
                            | "running"
                            | "paused"
                            | "completed"
                            | "cancelled"
                            | "failed"
                        }
                      />
                    </td>
                    <td className="p-4 text-right">
                      <span className="font-medium">
                        {scan.processed_items.toLocaleString()}
                      </span>
                      <span className="text-muted-foreground">
                        /{scan.total_items.toLocaleString()}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <span
                        className={
                          scan.issues_found > 0
                            ? "font-medium text-yellow-600 dark:text-yellow-400"
                            : ""
                        }
                      >
                        {scan.issues_found}
                      </span>
                    </td>
                    <td className="p-4 text-right text-muted-foreground">
                      {formatDuration(scan.started_at, scan.completed_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-4">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
            >
              Previous
            </button>
            <span className="text-sm text-muted-foreground">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-muted"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
