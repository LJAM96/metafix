"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { RefreshCw } from "lucide-react";

export function PlexSettingsCard() {
  const router = useRouter();
  const [disconnecting, setDisconnecting] = useState(false);
  const [plexStatus, setPlexStatus] = useState<{
    connected: boolean;
    server_name?: string;
    server_url?: string;
  } | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    fetchPlexStatus();
  }, []);

  async function fetchPlexStatus() {
    try {
      const res = await api.plex.status();
      if (res.data) {
        setPlexStatus(res.data);
      }
    } catch (error) {
      console.error("Failed to load Plex status:", error);
    }
  }

  async function handleDisconnect() {
    setDisconnecting(true);
    try {
      const res = await fetch("/api/plex/disconnect", { method: "DELETE" });
      if (res.ok) {
        toast({
          title: "Success",
          description: "Disconnected from Plex",
        });
        setPlexStatus({ connected: false });
      } else {
        throw new Error("Failed to disconnect");
      }
    } catch (error) {
      console.error("Failed to disconnect:", error);
      toast({
        title: "Error",
        description: "Failed to disconnect from Plex",
        variant: "destructive",
      });
    } finally {
      setDisconnecting(false);
    }
  }

  async function handleReconnect() {
    router.push("/onboarding");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Plex Connection</CardTitle>
        <CardDescription>
          Manage your connection to Plex.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {plexStatus?.connected ? (
          <>
            <div className="grid gap-2">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <div className="font-medium">
                    {plexStatus.server_name || "Plex Server"}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {plexStatus.server_url}
                  </div>
                </div>
                <div className="text-sm font-medium text-green-600">
                  ✅ Connected
                </div>
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleDisconnect}
                disabled={disconnecting}
              >
                {disconnecting ? "Disconnecting..." : "Disconnect"}
              </Button>
              <Button
                variant="outline"
                onClick={handleReconnect}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Change Server
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-muted-foreground text-sm">
              Not connected to Plex. Connect to get started.
            </p>
            <Button onClick={handleReconnect}>
              Connect to Plex
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
