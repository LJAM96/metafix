/**
 * SSE client for scan progress updates
 */

export type ScanEventHandler = (event: ScanEvent) => void;

export interface ScanEvent {
  type: "connected" | "progress" | "scan_paused" | "scan_resumed" | "scan_completed" | "scan_cancelled" | "error";
  scan_id?: number;
  processed?: number;
  total?: number;
  current_item?: string;
  current_library?: string;
  message?: string;
}

export class ScanClient {
  private eventSource: EventSource | null = null;
  private handlers: Set<ScanEventHandler> = new Set();

  connect(): void {
    if (this.eventSource) {
      return;
    }

    this.eventSource = new EventSource("/api/scan/subscribe");

    this.eventSource.onopen = () => {
      console.log("SSE connection established");
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ScanEvent;
        this.handlers.forEach((handler) => handler(data));
      } catch (error) {
        console.error("Failed to parse SSE message:", error);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error("SSE error:", error);
      this.handlers.forEach((handler) =>
        handler({ type: "error", message: "Connection lost" })
      );
      this.disconnect();
      // Attempt to reconnect after 5 seconds
      setTimeout(() => this.connect(), 5000);
    };
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  subscribe(handler: ScanEventHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }
}

// Singleton instance
export const scanClient = new ScanClient();
