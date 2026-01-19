"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

type Step = "plex" | "libraries" | "providers" | "complete";

interface Library {
  id: string;
  name: string;
  type: string;
  item_count: number;
}

interface PlexServer {
  name: string;
  product: string;
  version: string;
  connections: Array<{ uri: string; local: boolean }>;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("plex");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Plex connection
  const [plexUrl, setPlexUrl] = useState("");
  const [plexToken, setPlexToken] = useState("");
  const [serverName, setServerName] = useState<string | null>(null);
  
  // OAuth state
  const [oauthPinId, setOauthPinId] = useState<number | null>(null);
  const [oauthCode, setOauthCode] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [detectedServers, setDetectedServers] = useState<PlexServer[]>([]);
  const [selectedServerUri, setSelectedServerUri] = useState<string>("");
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Libraries
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<Set<string>>(new Set());

  // Provider keys
  const [tmdbKey, setTmdbKey] = useState("");
  const [fanartKey, setFanartKey] = useState("");

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  async function startPlexOAuth() {
    setOauthLoading(true);
    setError(null);
    try {
        // Generate Client ID (random string)
        const clientId = "MetaFix-" + Math.random().toString(36).substring(2, 15);
        const res = await api.plex.auth.createPin(clientId);
        
        if (res.data) {
            setOauthPinId(res.data.id);
            setOauthCode(res.data.code);
            
            // Open auth window
            window.open(res.data.auth_url, "_blank", "width=600,height=700");
            
            // Start polling
            pollIntervalRef.current = setInterval(async () => {
                const check = await api.plex.auth.checkPin(res.data!.id, res.data!.code, clientId);
                if (check.data?.authorized && check.data.auth_token) {
                    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                    setPlexToken(check.data.auth_token);
                    await fetchPlexResources(check.data.auth_token);
                }
            }, 2000);
        }
    } catch (e) {
        setError("Failed to start Plex authentication");
        setOauthLoading(false);
    }
  }

  async function fetchPlexResources(token: string) {
      try {
          // We need an endpoint to get resources (servers) using the token
          // Since we implemented it in backend/routers/plex.py as POST /resources
          // But api.ts might not have it yet? I need to check if I added it to api.ts
          // I didn't add it to api.ts explicitly in my previous edit?
          // I added createPin and checkPin.
          // I will use raw fetch for now if api.ts is missing it, or assume it's there.
          // Wait, I didn't add `resources` to `api.ts`.
          // I'll implement raw fetch here.
          
          const res = await fetch("/api/plex/resources", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token })
          });
          
          if (res.ok) {
              const data = await res.json();
              const servers = data.servers || [];
              setDetectedServers(servers);
              if (servers.length > 0) {
                  // Pick first local connection if available, else first connection
                  const firstServer = servers[0];
                  const bestConn = firstServer.connections.find((c: any) => c.local) || firstServer.connections[0];
                  if (bestConn) setSelectedServerUri(bestConn.uri);
              }
              setOauthLoading(false); // Auth done, now selecting server
          }
      } catch (e) {
          setError("Failed to fetch Plex servers");
          setOauthLoading(false);
      }
  }

  async function handleConnectSelectedServer() {
      if (!selectedServerUri || !plexToken) return;
      await handlePlexConnect(selectedServerUri, plexToken);
  }

  async function handlePlexConnect(url: string, token: string) {
    setLoading(true);
    setError(null);

    try {
      const response = await api.plex.connect(url, token);

      if (response.error || !response.data?.success) {
        setError(response.error || response.data?.message || "Failed to connect to Plex");
        return;
      }

      setServerName(response.data.server_name || "Plex Server");
      
      // Fetch libraries
      await fetchLibraries();
      setStep("libraries");
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchLibraries() {
    try {
      const response = await api.plex.libraries();
      if (response.data) {
        setLibraries(response.data.libraries || []);
        setSelectedLibraries(new Set(response.data.libraries.map((lib) => lib.id)));
      }
    } catch (err) {
      console.error("Failed to fetch libraries:", err);
    }
  }

  function toggleLibrary(id: string) {
    const newSelected = new Set(selectedLibraries);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedLibraries(newSelected);
  }

  function selectAllLibraries() {
    setSelectedLibraries(new Set(libraries.map(lib => lib.id)));
  }

  function deselectAllLibraries() {
    setSelectedLibraries(new Set());
  }

  async function handleLibrariesContinue() {
    setStep("providers");
  }

  async function handleSaveProviders() {
    setLoading(true);
    setError(null);

    try {
      const response = await api.settings.updateProviders({
          tmdb_api_key: tmdbKey || null,
          fanart_api_key: fanartKey || null,
      });

      if (response.error) {
        setError("Failed to save provider settings");
        return;
      }

      setStep("complete");
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleFinish() {
    router.push("/");
  }

  const steps = ["plex", "libraries", "providers", "complete"];
  const currentStepIndex = steps.indexOf(step);

  return (
    <div className="max-w-xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">Setup MetaFix</h1>
        <p className="text-muted-foreground">
          Let's get you connected and ready to manage your Plex library.
        </p>
      </div>

      {/* Progress indicator */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === s
                  ? "bg-primary text-primary-foreground"
                  : currentStepIndex > i
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {i + 1}
            </div>
            {i < steps.length - 1 && (
              <div className="w-8 h-0.5 bg-muted mx-1" />
            )}
          </div>
        ))}
      </div>

      {step === "plex" && (
        <Card>
          <CardHeader>
            <CardTitle>Connect to Plex</CardTitle>
            <CardDescription>
              Sign in to your Plex account or enter details manually.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="oauth" className="w-full">
                <TabsList className="grid w-full grid-cols-2 mb-4">
                    <TabsTrigger value="oauth">Sign In</TabsTrigger>
                    <TabsTrigger value="manual">Manual</TabsTrigger>
                </TabsList>
                
                <TabsContent value="oauth" className="space-y-4">
                    {!detectedServers.length ? (
                        <div className="text-center py-4 space-y-4">
                            <p className="text-sm text-muted-foreground">
                                Sign in with your Plex account to discover servers automatically.
                            </p>
                            <Button 
                                onClick={startPlexOAuth} 
                                disabled={oauthLoading} 
                                className="w-full" 
                                variant="outline"
                            >
                                {oauthLoading ? "Waiting for browser login..." : "Sign in with Plex"}
                            </Button>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <Label>Select Server</Label>
                                <Select value={selectedServerUri} onValueChange={setSelectedServerUri}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select a server" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {detectedServers.map((server, idx) => (
                                            <div key={idx}>
                                                {server.connections.map((conn, cIdx) => (
                                                    <SelectItem key={`${idx}-${cIdx}`} value={conn.uri}>
                                                        {server.name} ({conn.local ? "Local" : "Remote"})
                                                    </SelectItem>
                                                ))}
                                            </div>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <Button onClick={handleConnectSelectedServer} disabled={!selectedServerUri || loading} className="w-full">
                                {loading ? "Connecting..." : "Connect"}
                            </Button>
                        </div>
                    )}
                </TabsContent>
                
                <TabsContent value="manual" className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="plex-url">Server URL</Label>
                      <Input
                        id="plex-url"
                        type="url"
                        placeholder="http://192.168.1.100:32400"
                        value={plexUrl}
                        onChange={(e) => setPlexUrl(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="plex-token">Plex Token</Label>
                      <Input
                        id="plex-token"
                        type="password"
                        placeholder="Enter your Plex token"
                        value={plexToken}
                        onChange={(e) => setPlexToken(e.target.value)}
                      />
                    </div>
                    <Button
                      className="w-full"
                      onClick={() => handlePlexConnect(plexUrl, plexToken)}
                      disabled={!plexUrl || !plexToken || loading}
                    >
                      {loading ? "Connecting..." : "Connect"}
                    </Button>
                </TabsContent>
            </Tabs>

            {error && (
              <div className="mt-4 bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {step === "libraries" && (
        <Card>
          <CardHeader>
            <CardTitle>Select Libraries</CardTitle>
            <CardDescription>
              Connected to: {serverName}. Choose which libraries to manage.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2 text-sm">
              <button onClick={selectAllLibraries} className="text-primary hover:underline">Select all</button>
              <span className="text-muted-foreground">|</span>
              <button onClick={deselectAllLibraries} className="text-primary hover:underline">Deselect all</button>
            </div>

            <div className="space-y-2">
              {libraries.length === 0 ? (
                <p className="text-muted-foreground text-sm py-4 text-center">
                  No video libraries found.
                </p>
              ) : (
                libraries.map((lib) => (
                  <label
                    key={lib.id}
                    className="flex items-center space-x-3 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors"
                  >
                    <Checkbox
                      checked={selectedLibraries.has(lib.id)}
                      onCheckedChange={() => toggleLibrary(lib.id)}
                    />
                    <div className="flex-1">
                      <div className="font-medium">{lib.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {lib.type === "movie" ? "Movies" : "TV Shows"} - {lib.item_count.toLocaleString()} items
                      </div>
                    </div>
                  </label>
                ))
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep("plex")}>Back</Button>
              <Button
                className="flex-1"
                onClick={handleLibrariesContinue}
                disabled={selectedLibraries.size === 0}
              >
                Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "providers" && (
        <Card>
          <CardHeader>
            <CardTitle>Configure Providers (Optional)</CardTitle>
            <CardDescription>
              Add API keys for better artwork sources.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tmdb-key">TMDB API Key</Label>
              <Input
                id="tmdb-key"
                type="password"
                placeholder="Enter TMDB API key (recommended)"
                value={tmdbKey}
                onChange={(e) => setTmdbKey(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fanart-key">Fanart.tv API Key</Label>
              <Input
                id="fanart-key"
                type="password"
                placeholder="Enter Fanart.tv API key (optional)"
                value={fanartKey}
                onChange={(e) => setFanartKey(e.target.value)}
              />
            </div>

            {error && (
              <div className="bg-destructive/10 text-destructive text-sm p-3 rounded-md">
                {error}
              </div>
            )}

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep("libraries")}>Back</Button>
              <Button variant="outline" onClick={() => setStep("complete")}>Skip</Button>
              <Button className="flex-1" onClick={handleSaveProviders} disabled={loading}>
                {loading ? "Saving..." : "Save & Continue"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === "complete" && (
        <Card>
          <CardHeader>
            <CardTitle>Setup Complete!</CardTitle>
            <CardDescription>
              MetaFix is ready to manage your Plex library.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-muted p-4 rounded-lg space-y-3">
              <p className="font-medium">Configuration Summary</p>
              <div className="text-sm space-y-1">
                <p><span className="text-muted-foreground">Server:</span> {serverName}</p>
                <p><span className="text-muted-foreground">Libraries:</span> {selectedLibraries.size} selected</p>
                <p><span className="text-muted-foreground">TMDB:</span> {tmdbKey ? "Configured" : "Not configured"}</p>
                <p><span className="text-muted-foreground">Fanart.tv:</span> {fanartKey ? "Configured" : "Not configured"}</p>
              </div>
            </div>

            <div className="bg-muted p-4 rounded-lg space-y-2">
              <p className="font-medium">What's next?</p>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>Run your first scan to detect artwork issues</li>
                <li>Review and fix detected problems</li>
                <li>Set up scheduled scans for automation</li>
              </ul>
            </div>

            <Button className="w-full" onClick={handleFinish}>
              Go to Dashboard
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
