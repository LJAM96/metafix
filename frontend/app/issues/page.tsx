"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { IssueCard, Issue } from "@/components/issue-card";

export default function IssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [filter, setFilter] = useState("pending");
  const { toast } = useToast();

  useEffect(() => {
    fetchIssues();
  }, [page, filter]);

  async function fetchIssues() {
    setLoading(true);
    try {
      const res = await api.issues.list({
        page,
        status: filter,
      });
      if (res.data) {
        const data: any = res.data;
        setIssues(data.issues);
        setHasMore(data.total > page * data.page_size);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleAutoFix() {
    if (!confirm("Are you sure you want to automatically apply top artwork suggestions for all pending issues?")) return;
    try {
        await api.autofix.start({skip_unmatched: true});
        toast({
            title: "Success",
            description: "Auto-fix started in background",
        });
    } catch (e) {
        toast({
            title: "Error",
            description: "Failed to start auto-fix",
            variant: "destructive",
        });
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Issues</h1>
        <div className="flex gap-2">
          {filter === "pending" && (
            <Button onClick={handleAutoFix} className="mr-4" variant="secondary">
              ✨ Auto-Fix All
            </Button>
          )}
          <Button 
            variant={filter === "pending" ? "default" : "outline"}
            onClick={() => setFilter("pending")}
          >
            Pending
          </Button>
          <Button 
            variant={filter === "skipped" ? "default" : "outline"}
            onClick={() => setFilter("rejected")} // Mapped to rejected backend status
          >
            Skipped
          </Button>
          <Button 
            variant={filter === "applied" ? "default" : "outline"}
            onClick={() => setFilter("applied")}
          >
            Resolved
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {issues.map((issue) => (
          <IssueCard key={issue.id} issue={issue} onResolve={fetchIssues} />
        ))}
        
        {loading && (
            <div className="flex justify-center p-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        )}
        
        {!loading && issues.length === 0 && (
            <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
                No issues found with current filter.
            </div>
        )}
      </div>

      <div className="flex justify-center gap-2 py-4">
        <Button 
            variant="outline" 
            disabled={page === 1 || loading}
            onClick={() => setPage(p => p - 1)}
        >
            Previous
        </Button>
        <Button 
            variant="outline" 
            disabled={!hasMore || loading}
            onClick={() => setPage(p => p + 1)}
        >
            Next
        </Button>
      </div>
    </div>
  );
}
