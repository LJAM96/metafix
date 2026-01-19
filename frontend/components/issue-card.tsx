"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { ArtworkPicker } from "@/components/artwork-picker";
import { api } from "@/lib/api";

export interface Issue {
  id: number;
  plex_rating_key: string;
  title: string;
  year: number | null;
  media_type: string;
  issue_type: string;
  status: string;
  library_name: string;
  suggestions: Suggestion[];
  details?: string;
}

export interface Suggestion {
  id: number;
  source: string;
  artwork_type: string;
  image_url: string;
  thumbnail_url: string | null;
  language: string | null;
  score: number;
  set_name: string | null;
  creator_name: string | null;
  is_selected: boolean;
}

interface IssueCardProps {
  issue: Issue;
  onResolve: () => void;
}

export function IssueCard({ issue, onResolve }: IssueCardProps) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const topSuggestions = issue.suggestions.slice(0, 4);

  async function handleAccept(suggestion: Suggestion) {
    setLoading(true);
    try {
      const res = await api.issues.accept(issue.id, suggestion.id);
      if (res.error) {
        toast({
            title: "Error",
            description: "Failed to apply artwork: " + res.error,
            variant: "destructive",
        });
      } else {
        onResolve();
      }
    } catch (e) {
      toast({
            title: "Error",
            description: "Failed to apply artwork",
            variant: "destructive",
        });
    } finally {
      setLoading(false);
    }
  }

  async function handleSkip() {
    setLoading(true);
    try {
      await api.issues.skip(issue.id);
      onResolve();
    } catch (e) {
      toast({
            title: "Error",
            description: "Failed to skip issue",
            variant: "destructive",
        });
    } finally {
      setLoading(false);
    }
  }

  function formatIssueType(type: string) {
    return type.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
  }

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-0 flex flex-col md:flex-row">
        {/* Info Column */}
        <div className="p-6 flex-1 border-r border-border/50">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="font-bold text-lg">{issue.title}</h3>
                {issue.year && <span className="text-muted-foreground">({issue.year})</span>}
              </div>
              <div className="flex gap-2 mb-2">
                <Badge variant="outline">{issue.library_name}</Badge>
                <Badge variant="destructive">{formatIssueType(issue.issue_type)}</Badge>
              </div>
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <Button variant="outline" size="sm" onClick={() => setPickerOpen(true)}>
              Browse All
            </Button>
            <Button variant="ghost" size="sm" onClick={handleSkip} disabled={loading}>
              Skip
            </Button>
          </div>
        </div>

        {/* Suggestions Column */}
        <div className="p-6 bg-muted/10 flex-1">
          <h4 className="text-sm font-medium mb-3 text-muted-foreground">Suggested Artwork</h4>
          {topSuggestions.length > 0 ? (
            <div className="grid grid-cols-4 gap-2">
              {topSuggestions.map((suggestion) => (
                <div key={suggestion.id} className="group relative aspect-[2/3] bg-muted rounded overflow-hidden cursor-pointer" onClick={() => handleAccept(suggestion)}>
                  <img
                    src={suggestion.thumbnail_url || suggestion.image_url}
                    alt={suggestion.source}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <Button size="sm" variant="secondary" className="h-6 text-xs px-2">
                      Apply
                    </Button>
                  </div>
                  <div className="absolute bottom-0 right-0 left-0 bg-gradient-to-t from-black/80 to-transparent p-1.5 pt-4">
                    <div className="flex justify-between items-end">
                      <span className="text-[10px] text-white/90 uppercase font-semibold">{suggestion.source}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-muted-foreground border-2 border-dashed rounded-lg p-4">
              No suggestions found
            </div>
          )}
        </div>
      </CardContent>

      <ArtworkPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        suggestions={issue.suggestions}
        title={issue.title}
        onSelect={(s) => {
          handleAccept(s);
          setPickerOpen(false);
        }}
      />
    </Card>
  );
}
