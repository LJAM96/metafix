"use client";

import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Pause, Play, X } from "lucide-react";

export interface ScanProgress {
  scan_id: number;
  status: "pending" | "running" | "paused" | "completed" | "cancelled" | "failed";
  processed: number;
  total: number;
  issues_found: number;
  editions_updated?: number;
  current_item?: string;
  current_library?: string;
}

interface ScanProgressCardProps {
  progress: ScanProgress;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  showControls?: boolean;
}

export function ScanProgressCard({
  progress,
  onPause,
  onResume,
  onCancel,
  showControls = true,
}: ScanProgressCardProps) {
  const progressPercent =
    progress.total > 0
      ? Math.round((progress.processed / progress.total) * 100)
      : 0;

  const isPaused = progress.status === "paused";
  const isRunning = progress.status === "running";
  const isActive = isRunning || isPaused;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {isPaused
              ? "Scan Paused"
              : isRunning
              ? "Scanning..."
              : progress.status === "completed"
              ? "Scan Complete"
              : "Scan " + progress.status}
          </CardTitle>
          <ScanStatusBadge status={progress.status} />
        </div>
        {progress.current_library && isActive && (
          <p className="text-sm text-muted-foreground">
            Library: {progress.current_library}
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{progressPercent}%</span>
          </div>
          <Progress value={progressPercent} className="h-2" />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Processed
            </div>
            <div className="text-xl font-bold mt-1">
              {progress.processed.toLocaleString()}
              <span className="text-sm font-normal text-muted-foreground">
                {" "}
                / {progress.total.toLocaleString()}
              </span>
            </div>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Issues Found
            </div>
            <div className="text-xl font-bold mt-1">
              {progress.issues_found.toLocaleString()}
            </div>
          </div>
        </div>

        {/* Current item */}
        {progress.current_item && isActive && (
          <div className="text-sm">
            <span className="text-muted-foreground">Current: </span>
            <span className="truncate">{progress.current_item}</span>
          </div>
        )}

        {/* Controls */}
        {showControls && isActive && (
          <div className="flex gap-2 pt-2">
            {isRunning ? (
              <Button variant="outline" size="sm" onClick={onPause}>
                <Pause className="w-4 h-4 mr-2" />
                Pause
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={onResume}>
                <Play className="w-4 h-4 mr-2" />
                Resume
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={onCancel}>
              <X className="w-4 h-4 mr-2" />
              Cancel
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ScanStatusBadgeProps {
  status: ScanProgress["status"];
}

export function ScanStatusBadge({ status }: ScanStatusBadgeProps) {
  const styles: Record<ScanProgress["status"], string> = {
    pending: "bg-muted text-muted-foreground",
    running: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    paused: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
    completed: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    cancelled: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    failed: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  };

  const labels: Record<ScanProgress["status"], string> = {
    pending: "Pending",
    running: "Running",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
    failed: "Failed",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}
    >
      {status === "running" && (
        <span className="w-2 h-2 bg-current rounded-full mr-1.5 animate-pulse" />
      )}
      {labels[status]}
    </span>
  );
}
