"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

type Step = "plex" | "libraries" | "providers" | "complete";

interface Library {
  id: string;
  name: string;
  type: string;
  item_count: number;
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

  // Libraries
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [selectedLibraries, setSelectedLibraries] = useState<Set<string>>(new Set());

  // Provider keys
  const [tmdbKey, setTmdbKey] = useState("");
  const [fanartKey, setFanartKey] = useState("");

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
              Enter your Plex server URL and authentication token.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="plex-url">Server URL</Label>
                <Input
                  id="plex-url"
                  type="url"
                  placeholder="http://192.168.1.100:32400"
                  value={plexUrl}
                  onChange={(e) => setPlexUrl(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Your Plex server address (e.g., http://localhost:32400 or http://192.168.x.x:32400)
                </p>
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
                <p className="text-xs text-muted-foreground">
                  Find your token at{" "}
                  <a
                    href="https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    Plex Support
                  </a>
                </p>
              </div>
              <Button
                className="w-full"
                onClick={() => handlePlexConnect(plexUrl, plexToken)}
                disabled={!plexUrl || !plexToken || loading}
              >
                {loading ? "Connecting..." : "Connect"}
              </Button>
            </div>

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
