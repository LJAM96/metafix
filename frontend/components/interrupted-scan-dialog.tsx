"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { AlertCircle, Loader2 } from "lucide-react";

interface InterruptedScan {
  id: number;
  scan_type: string;
  status: string;
  total_items: number;
  processed_items: number;
  issues_found: number;
  started_at: string;
  libraries: string[];
}

interface InterruptedScanDialogProps {
  onResolved?: () => void;
}

export function InterruptedScanDialog({
  onResolved,
}: InterruptedScanDialogProps) {
  const [open, setOpen] = useState(false);
  const [interruptedScan, setInterruptedScan] =
    useState<InterruptedScan | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    checkForInterruptedScan();
  }, []);

  async function checkForInterruptedScan() {
    try {
      const response = await fetch("/api/scan/interrupted");
      if (response.ok) {
        const data = await response.json();
        if (data.scan) {
          setInterruptedScan(data.scan);
          setOpen(true);
        }
      }
    } catch (error) {
      console.error("Failed to check for interrupted scan:", error);
    }
  }

  async function handleResume() {
    if (!interruptedScan) return;
    setLoading(true);

    try {
      const response = await fetch("/api/scan/resume", { method: "POST" });
      if (response.ok) {
        setOpen(false);
        router.push("/scan");
        onResolved?.();
      }
    } catch (error) {
      console.error("Failed to resume scan:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleDiscard() {
    setLoading(true);

    try {
      const response = await fetch("/api/scan/interrupted/discard", {
        method: "POST",
      });
      if (response.ok) {
        setOpen(false);
        onResolved?.();
      }
    } catch (error) {
      console.error("Failed to discard scan:", error);
    } finally {
      setLoading(false);
    }
  }

  if (!interruptedScan) return null;

  const progressPercent =
    interruptedScan.total_items > 0
      ? Math.round(
          (interruptedScan.processed_items / interruptedScan.total_items) * 100
        )
      : 0;

  const scanTypeLabel =
    interruptedScan.scan_type === "artwork"
      ? "Artwork Scan"
      : interruptedScan.scan_type === "edition"
      ? "Edition Scan"
      : "Full Scan";

  const startedDate = new Date(interruptedScan.started_at);
  const timeAgo = getTimeAgo(startedDate);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-yellow-500" />
            Interrupted Scan Detected
          </DialogTitle>
          <DialogDescription>
            A {scanTypeLabel.toLowerCase()} was interrupted {timeAgo}. Would you
            like to resume where it left off?
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Progress info */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span className="font-medium">
                {interruptedScan.processed_items.toLocaleString()} /{" "}
                {interruptedScan.total_items.toLocaleString()} items (
                {progressPercent}%)
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Type:</span>{" "}
              <span className="font-medium">{scanTypeLabel}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Issues found:</span>{" "}
              <span className="font-medium">
                {interruptedScan.issues_found}
              </span>
            </div>
            {interruptedScan.libraries && interruptedScan.libraries.length > 0 && (
              <div className="col-span-2">
                <span className="text-muted-foreground">Libraries:</span>{" "}
                <span className="font-medium">
                  {interruptedScan.libraries.join(", ")}
                </span>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={handleDiscard} disabled={loading}>
            Discard
          </Button>
          <Button onClick={handleResume} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Loading...
              </>
            ) : (
              "Resume Scan"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function getTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
}
