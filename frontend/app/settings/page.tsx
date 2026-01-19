"use client";

import { useEffect, useState } from "react";
import { PlexSettingsCard } from "./plex-settings-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { ArrowDown, ArrowUp } from "lucide-react";

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  
  // Provider Settings
  const [fanartKey, setFanartKey] = useState("");
  const [mediuxKey, setMediuxKey] = useState("");
  const [tmdbKey, setTmdbKey] = useState("");
  const [tvdbKey, setTvdbKey] = useState("");
  
  const [configured, setConfigured] = useState({
    fanart: false,
    mediux: false,
    tmdb: false,
    tvdb: false,
  });
  
  const [priority, setPriority] = useState<string[]>([]);
  const { toast } = useToast();

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    setLoading(true);
    try {
      const res = await api.settings.providers();
      if (res.data) {
        const data: any = res.data;
        setConfigured({
          fanart: data.fanart.configured,
          mediux: data.mediux.configured,
          tmdb: data.tmdb.configured,
          tvdb: data.tvdb.configured,
        });
        setPriority(data.provider_priority || []);
        
        // We don't get actual keys back, just status. 
        // Inputs will remain empty unless we want to indicate "Configured"
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveProviders() {
    setSaving(true);
    try {
      const payload: any = {
        provider_priority: priority,
      };
      
      // Only send keys if they were entered
      if (fanartKey) payload.fanart_api_key = fanartKey;
      if (mediuxKey) payload.mediux_api_key = mediuxKey;
      if (tmdbKey) payload.tmdb_api_key = tmdbKey;
      if (tvdbKey) payload.tvdb_api_key = tvdbKey;

      const res = await api.settings.updateProviders(payload);
      if (res.data) {
        // Refresh status
        await fetchSettings();
        // Clear inputs
        setFanartKey("");
        setMediuxKey("");
        setTmdbKey("");
        setTvdbKey("");
        toast({
            title: "Success",
            description: "Settings saved successfully",
        });
      }
    } catch (error) {
      console.error("Failed to save settings:", error);
      toast({
            title: "Error",
            description: "Failed to save settings",
            variant: "destructive",
        });
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(provider: string) {
    setTesting(provider);
    try {
      const res = await fetch(`/api/settings/providers/test/${provider}`, {
        method: "POST",
      });
      const data = await res.json();
      toast({
            title: "Test Result",
            description: `${provider.toUpperCase()}: ${data.message}`,
        });
    } catch (error) {
      toast({
            title: "Error",
            description: `Failed to test ${provider}`,
            variant: "destructive",
        });
    } finally {
      setTesting(null);
    }
  }

  function movePriority(index: number, direction: "up" | "down") {
    if (direction === "up" && index > 0) {
      const newPriority = [...priority];
      [newPriority[index - 1], newPriority[index]] = [
        newPriority[index],
        newPriority[index - 1],
      ];
      setPriority(newPriority);
    } else if (direction === "down" && index < priority.length - 1) {
      const newPriority = [...priority];
      [newPriority[index + 1], newPriority[index]] = [
        newPriority[index],
        newPriority[index + 1],
      ];
      setPriority(newPriority);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-6">
      <h1 className="text-3xl font-bold mb-6">Settings</h1>

      <Tabs defaultValue="providers" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="providers">Metadata Providers</TabsTrigger>
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="plex">Plex Connection</TabsTrigger>
        </TabsList>

        <TabsContent value="providers">
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Provider Configuration</CardTitle>
                <CardDescription>
                  Configure API keys for metadata providers. Leave blank to keep
                  existing keys.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Fanart.tv */}
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="fanart">Fanart.tv</Label>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {configured.fanart ? "✅ Configured" : "⚠️ Not configured"}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest("fanart")}
                        disabled={testing === "fanart" || (!configured.fanart && !fanartKey)}
                      >
                        {testing === "fanart" ? "Testing..." : "Test"}
                      </Button>
                    </div>
                  </div>
                  <Input
                    id="fanart"
                    type="password"
                    placeholder="Enter API Key"
                    value={fanartKey}
                    onChange={(e) => setFanartKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Required for HD logos, clearart, and movie posters.
                  </p>
                </div>

                {/* TMDB */}
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tmdb">The Movie Database (TMDB)</Label>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {configured.tmdb ? "✅ Configured" : "⚠️ Not configured"}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest("tmdb")}
                        disabled={testing === "tmdb" || (!configured.tmdb && !tmdbKey)}
                      >
                        {testing === "tmdb" ? "Testing..." : "Test"}
                      </Button>
                    </div>
                  </div>
                  <Input
                    id="tmdb"
                    type="password"
                    placeholder="Enter API Key (v3 auth)"
                    value={tmdbKey}
                    onChange={(e) => setTmdbKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Required for movie metadata and artwork.
                  </p>
                </div>

                {/* TVDB */}
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="tvdb">The TVDB (v4)</Label>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {configured.tvdb ? "✅ Configured" : "⚠️ Not configured"}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest("tvdb")}
                        disabled={testing === "tvdb" || (!configured.tvdb && !tvdbKey)}
                      >
                        {testing === "tvdb" ? "Testing..." : "Test"}
                      </Button>
                    </div>
                  </div>
                  <Input
                    id="tvdb"
                    type="password"
                    placeholder="Enter Project API Key"
                    value={tvdbKey}
                    onChange={(e) => setTvdbKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Required for TV show metadata.
                  </p>
                </div>

                {/* Mediux */}
                <div className="grid gap-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="mediux">Mediux</Label>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        {configured.mediux ? "✅ Configured" : "⚪ Optional"}
                      </span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleTest("mediux")}
                        disabled={testing === "mediux"}
                      >
                        {testing === "mediux" ? "Testing..." : "Test"}
                      </Button>
                    </div>
                  </div>
                  <Input
                    id="mediux"
                    type="password"
                    placeholder="Enter API Key (Optional)"
                    value={mediuxKey}
                    onChange={(e) => setMediuxKey(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Community curated artwork sets.
                  </p>
                </div>

                <div className="pt-4">
                  <Button onClick={handleSaveProviders} disabled={saving}>
                    {saving ? "Saving..." : "Save Configuration"}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Provider Priority</CardTitle>
                <CardDescription>
                  Drag and drop to reorder providers. Higher priority providers are checked first.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {priority.map((provider, index) => (
                    <div
                      key={provider}
                      className="flex items-center justify-between p-3 border rounded-md bg-card"
                    >
                      <span className="capitalize font-medium">
                        {index + 1}. {provider}
                      </span>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={index === 0}
                          onClick={() => movePriority(index, "up")}
                        >
                          <ArrowUp className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={index === priority.length - 1}
                          onClick={() => movePriority(index, "down")}
                        >
                          <ArrowDown className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4">
                  <Button
                    variant="outline"
                    onClick={handleSaveProviders}
                    disabled={saving}
                  >
                    Update Priority
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
              <CardDescription>
                Application-wide preferences.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-sm">
                General settings coming soon.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="plex">
          <PlexSettingsCard />
        </TabsContent>
      </Tabs>
    </div>
  );
}
