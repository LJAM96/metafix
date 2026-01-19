"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { api } from "@/lib/api";
import { ScanProgressCard, ScanProgress as CardScanProgress } from "@/components/scan-progress";

// Local interface matching API response
interface ScanStatusData {
  id: number;
  scan_type: string;
  status: "pending" | "running" | "paused" | "completed" | "cancelled" | "failed";
  total_items: number;
  processed_items: number;
  issues_found: number;
  current_item?: string;
  current_library?: string;
}

export default function ScanPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [pageState, setPageState] = useState<"config" | "running" | "completed">("config");
  const [error, setError] = useState<string | null>(null);

  // Config
  const [libraries, setLibraries] = useState<Array<{ id: string; name: string; item_count: number }>>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<Set<string>>(new Set());
  const [scanType, setScanType] = useState<"artwork" | "edition" | "both">("both");
  
  // Artwork options
  const [checkPosters, setCheckPosters] = useState(true);
  const [checkBackgrounds, setCheckBackgrounds] = useState(true);
  const [checkLogos, setCheckLogos] = useState(true);
  const [checkUnmatched, setCheckUnmatched] = useState(true);
  const [checkPlaceholders, setCheckPlaceholders] = useState(true);

  // Progress
  const [progress, setProgress] = useState<ScanStatusData | null>(null);

  useEffect(() => {
    loadLibraries();
    checkActiveScan();
    
    // Cleanup SSE on unmount
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  let eventSource: EventSource | null = null;

  async function loadLibraries() {
    try {
      const res = await api.plex.libraries();
      if (res.data) {
        setLibraries(res.data.libraries);
        // Select all by default
        setSelectedLibraries(new Set(res.data.libraries.map((l) => l.id)));
      }
    } catch (err) {
      console.error("Failed to load libraries:", err);
      setError("Failed to load libraries. Is Plex connected?");
    }
  }

  async function checkActiveScan() {
    try {
      const res = await api.scan.status();
      if (res.data && (res.data.status === "running" || res.data.status === "paused")) {
        setProgress(res.data as ScanStatusData);
        setPageState("running");
        subscribeToProgress();
      }
    } catch (err) {
      // No active scan or error
    }
  }

  function subscribeToProgress() {
    if (eventSource) return;

    eventSource = new EventSource("/api/scan/subscribe");
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "progress") {
        setProgress((prev) => {
            if (!prev) return null;
            return {
                ...prev,
                processed_items: data.processed,
                total_items: data.total,
                current_item: data.current_item,
                current_library: data.current_library,
                // issues_found usually updated separately or included in progress event? 
                // The backend ScanProgressEvent doesn't have issues_found. 
                // We might need to poll for issues count or add it to event.
                // For now keep prev issues or assume it updates via status events
            };
        });
      } else if (data.type === "status") {
        const newStatus = data.status;
        setProgress((prev) => prev ? { ...prev, status: newStatus } : null);
        
        if (newStatus === "completed") {
            setPageState("completed");
            eventSource?.close();
            eventSource = null;
        } else if (newStatus === "cancelled" || newStatus === "failed") {
            setPageState("config");
            setProgress(null);
            eventSource?.close();
            eventSource = null;
        }
      } else if (data.type === "issue") {
          // Increment issue count
          setProgress((prev) => prev ? { ...prev, issues_found: prev.issues_found + 1 } : null);
      }
    };
  }

  const toggleLibrary = (id: string) => {
    const newSet = new Set(selectedLibraries);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedLibraries(newSet);
  };

  async function startScan() {
    if (selectedLibraries.size === 0) {
      setError("Please select at least one library");
      return;
    }

    setLoading(true);
    setError(null);

    const config = {
      scan_type: scanType,
      libraries: Array.from(selectedLibraries),
      check_posters: checkPosters,
      check_backgrounds: checkBackgrounds,
      check_logos: checkLogos,
      check_unmatched: checkUnmatched,
      check_placeholders: checkPlaceholders,
      edition_enabled: scanType === "edition" || scanType === "both",
      backup_editions: true, // Default
    };

    try {
      const res = await api.scan.start(config);
      if (res.data) {
        // Init progress
        setProgress({
            id: res.data.scan_id,
            scan_type: scanType,
            status: "pending",
            total_items: 0,
            processed_items: 0,
            issues_found: 0,
        });
        setPageState("running");
        subscribeToProgress();
      } else if (res.error) {
        setError(res.error);
      }
    } catch (err) {
      console.error("Failed to start scan:", err);
      setError("Failed to start scan");
    } finally {
      setLoading(false);
    }
  }

  async function pauseScan() {
    await api.scan.pause();
    // Status update will come via SSE
  }

  async function resumeScan() {
    await api.scan.resume();
  }

  async function cancelScan() {
    await api.scan.cancel();
  }

  // Convert API status to CardStatus
  const cardProgress: CardScanProgress | null = progress ? {
      scan_id: progress.id,
      status: progress.status,
      processed: progress.processed_items,
      total: progress.total_items,
      issues_found: progress.issues_found,
      current_item: progress.current_item,
      current_library: progress.current_library,
  } : null;

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Scan Libraries</h1>

      {pageState === "config" && (
        <div className="space-y-6">
          {/* Scan Type */}
          <Card>
            <CardHeader>
              <CardTitle>Scan Type</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="scanType"
                  value="artwork"
                  checked={scanType === "artwork"}
                  onChange={() => setScanType("artwork")}
                  className="h-4 w-4"
                />
                <div>
                  <div className="font-medium">Artwork Only</div>
                  <div className="text-sm text-muted-foreground">
                    Find missing posters, backgrounds, and logos
                  </div>
                </div>
              </label>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="scanType"
                  value="edition"
                  checked={scanType === "edition"}
                  onChange={() => setScanType("edition")}
                  className="h-4 w-4"
                />
                <div>
                  <div className="font-medium">Edition Only</div>
                  <div className="text-sm text-muted-foreground">
                    Update edition metadata (Directors Cut, 4K, etc.)
                  </div>
                </div>
              </label>
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="radio"
                  name="scanType"
                  value="both"
                  checked={scanType === "both"}
                  onChange={() => setScanType("both")}
                  className="h-4 w-4"
                />
                <div>
                  <div className="font-medium">Both Artwork + Edition</div>
                  <div className="text-sm text-muted-foreground">
                    Full scan for all issues
                  </div>
                </div>
              </label>
            </CardContent>
          </Card>

          {/* Libraries */}
          <Card>
            <CardHeader>
              <CardTitle>Libraries</CardTitle>
              <CardDescription>
                Select which libraries to scan
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 max-h-60 overflow-y-auto">
              {libraries.map((lib) => (
                <label
                  key={lib.id}
                  className="flex items-center space-x-3 p-2 rounded hover:bg-muted/50 cursor-pointer"
                >
                  <Checkbox
                    checked={selectedLibraries.has(lib.id)}
                    onCheckedChange={() => toggleLibrary(lib.id)}
                  />
                  <div className="flex-1">
                    <span className="font-medium">{lib.name}</span>
                    <span className="text-sm text-muted-foreground ml-2">
                      ({lib.item_count.toLocaleString()} items)
                    </span>
                  </div>
                </label>
              ))}
            </CardContent>
          </Card>

          {/* Artwork Options */}
          {(scanType === "artwork" || scanType === "both") && (
            <Card>
              <CardHeader>
                <CardTitle>Artwork Options</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <label className="flex items-center space-x-3">
                  <Checkbox
                    checked={checkPosters}
                    onCheckedChange={(checked) => setCheckPosters(!!checked)}
                  />
                  <span>Missing posters</span>
                </label>
                <label className="flex items-center space-x-3">
                  <Checkbox
                    checked={checkBackgrounds}
                    onCheckedChange={(checked) => setCheckBackgrounds(!!checked)}
                  />
                  <span>Missing backgrounds</span>
                </label>
                <label className="flex items-center space-x-3">
                  <Checkbox
                    checked={checkLogos}
                    onCheckedChange={(checked) => setCheckLogos(!!checked)}
                  />
                  <span>Missing logos</span>
                </label>
                <label className="flex items-center space-x-3">
                  <Checkbox
                    checked={checkUnmatched}
                    onCheckedChange={(checked) => setCheckUnmatched(!!checked)}
                  />
                  <span>Unmatched items</span>
                </label>
                <label className="flex items-center space-x-3">
                  <Checkbox
                    checked={checkPlaceholders}
                    onCheckedChange={(checked) => setCheckPlaceholders(!!checked)}
                  />
                  <span>Placeholder artwork (wrong aspect ratio)</span>
                </label>
              </CardContent>
            </Card>
          )}

          {error && (
            <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
              {error}
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/")}>
              Cancel
            </Button>
            <Button
              className="flex-1"
              onClick={startScan}
              disabled={selectedLibraries.size === 0 || loading}
            >
              {loading ? "Starting..." : "Start Scan"}
            </Button>
          </div>
        </div>
      )}

      {pageState === "running" && cardProgress && (
        <ScanProgressCard
            progress={cardProgress}
            onPause={pauseScan}
            onResume={resumeScan}
            onCancel={cancelScan}
        />
      )}

      {pageState === "completed" && cardProgress && (
        <Card>
          <CardHeader>
            <CardTitle>Scan Complete</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground">Items Scanned</div>
                <div className="text-2xl font-bold">
                  {cardProgress.processed.toLocaleString()}
                </div>
              </div>
              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground">Issues Found</div>
                <div className="text-2xl font-bold">
                  {cardProgress.issues_found.toLocaleString()}
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => router.push("/")}>
                Back to Dashboard
              </Button>
              <Button className="flex-1" onClick={() => router.push("/issues")}>
                Review Issues
              </Button>
            </div>
            
            <div className="pt-4 border-t">
                 <Button variant="ghost" onClick={() => setPageState("config")}>
                    Start New Scan
                 </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
