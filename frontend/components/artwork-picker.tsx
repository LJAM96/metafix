"use client";

import { useState } from "react";
import Image from "next/image";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Suggestion } from "./issue-card";

interface ArtworkPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  suggestions: Suggestion[];
  onSelect: (suggestion: Suggestion) => void;
  title: string;
}

export function ArtworkPicker({
  open,
  onOpenChange,
  suggestions,
  onSelect,
  title,
}: ArtworkPickerProps) {
  const [filter, setFilter] = useState<"all" | "poster" | "background" | "logo">("all");
  const [providerFilter, setProviderFilter] = useState<string>("all");

  const providers = Array.from(new Set(suggestions.map((s) => s.source)));
  
  const filteredSuggestions = suggestions.filter((s) => {
    if (filter !== "all" && s.artwork_type !== filter) return false;
    if (providerFilter !== "all" && s.source !== providerFilter) return false;
    return true;
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Artwork for {title}</DialogTitle>
          <DialogDescription>
            Choose from available suggestions.
          </DialogDescription>
        </DialogHeader>

        <div className="flex gap-4 py-4 border-b">
          <Tabs value={providerFilter} onValueChange={setProviderFilter} className="w-full">
            <TabsList>
              <TabsTrigger value="all">All Providers</TabsTrigger>
              {providers.map((p) => (
                <TabsTrigger key={p} value={p} className="capitalize">
                  {p}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        <div className="flex-1 overflow-y-auto min-h-0 p-1">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {filteredSuggestions.map((suggestion) => (
              <div
                key={suggestion.id}
                className="group relative border rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all"
                onClick={() => onSelect(suggestion)}
              >
                <div className="aspect-[2/3] relative bg-muted">
                  <img
                    src={suggestion.thumbnail_url || suggestion.image_url}
                    alt={suggestion.source}
                    className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    loading="lazy"
                  />
                  <div className="absolute top-2 right-2 flex gap-1">
                    <Badge variant="secondary" className="uppercase text-[10px]">
                      {suggestion.source}
                    </Badge>
                    {suggestion.language && (
                      <Badge variant="outline" className="uppercase text-[10px] bg-background/80">
                        {suggestion.language}
                      </Badge>
                    )}
                  </div>
                  
                  {suggestion.set_name && (
                    <div className="absolute bottom-0 left-0 right-0 p-2 bg-black/60 text-white text-xs truncate">
                        {suggestion.set_name}
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {filteredSuggestions.length === 0 && (
                <div className="col-span-full text-center py-10 text-muted-foreground">
                    No artwork found matching filters.
                </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
