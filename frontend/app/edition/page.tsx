"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { ArrowDown, ArrowUp } from "lucide-react";

interface EditionModule {
  name: string;
  description: string;
  example: string;
}

interface EditionConfig {
  enabled_modules: string[];
  module_order: string[];
  separator: string;
  excluded_languages: string[];
  skip_multiple_audio_tracks: boolean;
  rating_source: string;
  tmdb_api_key?: string;
}

export default function EditionPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [modules, setModules] = useState<EditionModule[]>([]);
  const [config, setConfig] = useState<EditionConfig | null>(null);
  const { toast } = useToast();
  
  // Preview
  const [previewKey, setPreviewKey] = useState("");
  const [previewResult, setPreviewResult] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    setLoading(true);
    try {
      const [modulesRes, configRes] = await Promise.all([
        api.edition.modules(),
        api.edition.config(),
      ]);
      
      if (modulesRes.data) {
        setModules(modulesRes.data.modules);
      }
      if (configRes.data) {
        setConfig(configRes.data as unknown as EditionConfig);
      }
    } catch (error) {
      console.error("Failed to fetch edition data:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!config) return;
    setSaving(true);
    try {
      await api.edition.updateConfig(config);
      toast({
          title: "Success",
          description: "Settings saved",
      });
    } catch (error) {
      console.error("Failed to save config:", error);
      toast({
          title: "Error",
          description: "Failed to save settings",
          variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  }

  function toggleModule(name: string) {
    if (!config) return;
    const enabled = new Set(config.enabled_modules);
    if (enabled.has(name)) {
      enabled.delete(name);
    } else {
      enabled.add(name);
    }
    setConfig({ ...config, enabled_modules: Array.from(enabled) });
  }

  function moveModule(index: number, direction: "up" | "down") {
    if (!config) return;
    const order = [...config.module_order];
    if (direction === "up" && index > 0) {
      [order[index - 1], order[index]] = [order[index], order[index - 1]];
    } else if (direction === "down" && index < order.length - 1) {
      [order[index + 1], order[index]] = [order[index], order[index + 1]];
    }
    setConfig({ ...config, module_order: order });
  }

  async function handlePreview() {
    if (!previewKey) return;
    setPreviewLoading(true);
    try {
        // We need to add preview endpoint to api.ts or fetch directly
        // Assuming api.ts doesn't have it yet, using fetch
        const res = await fetch(`/api/edition/preview?rating_key=${previewKey}`, {
            method: "POST"
        });
        if (res.ok) {
            const data = await res.json();
            setPreviewResult(data);
        } else {
            toast({
                title: "Error",
                description: "Preview failed. Check the rating key.",
                variant: "destructive",
            });
        }
    } catch (e) {
        console.error(e);
        toast({
            title: "Error",
            description: "Preview failed",
            variant: "destructive",
        });
    } finally {
        setPreviewLoading(false);
    }
  }

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Edition Manager</h1>
          <p className="text-muted-foreground">
            Configure how edition tags are generated for your movies.
          </p>
        </div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Module Order & Selection */}
        <Card className="md:col-span-1">
          <CardHeader>
            <CardTitle>Module Configuration</CardTitle>
            <CardDescription>
              Enable and reorder modules to customize the edition string.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {config.module_order.map((name, index) => {
              const moduleInfo = modules.find((m) => m.name === name) || {
                name,
                description: "Unknown module",
                example: "",
              };
              const isEnabled = config.enabled_modules.includes(name);

              return (
                <div
                  key={name}
                  className={`flex items-center justify-between p-3 border rounded-md ${
                    isEnabled ? "bg-card" : "bg-muted/50 opacity-70"
                  }`}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <Checkbox
                      checked={isEnabled}
                      onCheckedChange={() => toggleModule(name)}
                    />
                    <div className="min-w-0">
                      <div className="font-medium truncate">{moduleInfo.name}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        Example: {moduleInfo.example}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      disabled={index === 0}
                      onClick={() => moveModule(index, "up")}
                    >
                      <ArrowUp className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      disabled={index === config.module_order.length - 1}
                      onClick={() => moveModule(index, "down")}
                    >
                      <ArrowDown className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {/* General Settings */}
          <Card>
            <CardHeader>
              <CardTitle>General Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="separator">Separator</Label>
                <Input
                  id="separator"
                  value={config.separator}
                  onChange={(e) =>
                    setConfig({ ...config, separator: e.target.value })
                  }
                  placeholder=" . "
                />
                <p className="text-xs text-muted-foreground">
                  Character(s) used to separate edition parts.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="excluded">Excluded Languages</Label>
                <Input
                  id="excluded"
                  value={config.excluded_languages.join(", ")}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      excluded_languages: e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean),
                    })
                  }
                  placeholder="English"
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of languages to hide.
                </p>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox 
                    id="skip_audio" 
                    checked={config.skip_multiple_audio_tracks}
                    onCheckedChange={(c) => setConfig({...config, skip_multiple_audio_tracks: !!c})}
                />
                <Label htmlFor="skip_audio">Skip language if multiple tracks</Label>
              </div>
            </CardContent>
          </Card>
          
          {/* Preview */}
          <Card>
            <CardHeader>
                <CardTitle>Preview</CardTitle>
                <CardDescription>Test generation on a specific movie.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                <div className="flex gap-2">
                    <Input 
                        placeholder="Plex Rating Key (e.g. 12345)" 
                        value={previewKey}
                        onChange={(e) => setPreviewKey(e.target.value)}
                    />
                    <Button onClick={handlePreview} disabled={previewLoading || !previewKey}>
                        {previewLoading ? "..." : "Test"}
                    </Button>
                </div>
                
                {previewResult && (
                    <div className="mt-4 p-4 bg-muted rounded-md space-y-2">
                        <div>
                            <span className="text-xs text-muted-foreground uppercase">Result</span>
                            <div className="font-mono font-medium">{previewResult.new_edition || "(Empty)"}</div>
                        </div>
                    </div>
                )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
