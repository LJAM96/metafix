"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";

interface Schedule {
  id: number;
  name: string;
  enabled: boolean;
  cron_expression: string;
  scan_type: string;
  auto_commit: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
}

interface CronPreset {
  name: string;
  cron: string;
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [presets, setPresets] = useState<CronPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const { toast } = useToast();

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    cron_expression: "",
    scan_type: "both",
    auto_commit: false,
    auto_commit_skip_unmatched: true,
    auto_commit_min_score: 0,
    config: {
        check_posters: true,
        check_backgrounds: true,
        check_logos: true,
        check_unmatched: true,
        check_placeholders: true,
        edition_enabled: true,
    }
  });

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [schedRes, presetsRes] = await Promise.all([
        api.schedules.list(),
        api.schedules.presets(),
      ]);
      
      if (schedRes.data) {
        setSchedules(schedRes.data.schedules as any);
      }
      if (presetsRes.data) {
        setPresets(presetsRes.data.presets);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function handleCreate() {
    setEditingId(null);
    setFormData({
        name: "",
        cron_expression: "0 3 * * *",
        scan_type: "both",
        auto_commit: false,
        auto_commit_skip_unmatched: true,
        auto_commit_min_score: 0,
        config: {
            check_posters: true,
            check_backgrounds: true,
            check_logos: true,
            check_unmatched: true,
            check_placeholders: true,
            edition_enabled: true,
        }
    });
    setDialogOpen(true);
  }

  async function handleSave() {
    try {
        if (editingId) {
            await api.schedules.update(editingId, formData);
        } else {
            await api.schedules.create(formData);
        }
        setDialogOpen(false);
        loadData();
    } catch (e) {
        toast({
            title: "Error",
            description: "Failed to save schedule",
            variant: "destructive",
        });
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure you want to delete this schedule?")) return;
    await api.schedules.delete(id);
    loadData();
  }

  async function handleToggle(schedule: Schedule) {
    if (schedule.enabled) {
        await api.schedules.disable(schedule.id);
    } else {
        await api.schedules.enable(schedule.id);
    }
    loadData();
  }

  async function handleRun(id: number) {
    await api.schedules.run(id);
    toast({
        title: "Success",
        description: "Scan triggered",
    });
  }

  function formatTime(dateStr: string | null) {
    if (!dateStr) return "Never";
    return new Date(dateStr).toLocaleString();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Scheduled Scans</h1>
        <Button onClick={handleCreate}>+ New Schedule</Button>
      </div>

      <div className="grid gap-4">
        {schedules.map((schedule) => (
          <Card key={schedule.id}>
            <CardHeader className="pb-3">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {schedule.name}
                    {schedule.enabled ? (
                      <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Enabled</span>
                    ) : (
                      <span className="text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded-full">Disabled</span>
                    )}
                  </CardTitle>
                  <CardDescription className="font-mono text-xs mt-1">
                    {schedule.cron_expression} • {schedule.scan_type}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => handleRun(schedule.id)}>Run Now</Button>
                  <Button variant="outline" size="sm" onClick={() => handleToggle(schedule)}>
                    {schedule.enabled ? "Disable" : "Enable"}
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(schedule.id)}>Delete</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-muted-foreground grid grid-cols-2 gap-4">
                <div>Last run: {formatTime(schedule.last_run_at)}</div>
                <div>Auto-commit: {schedule.auto_commit ? "Yes" : "No"}</div>
              </div>
            </CardContent>
          </Card>
        ))}
        
        {schedules.length === 0 && (
            <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
                No schedules configured.
            </div>
        )}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Schedule" : "New Schedule"}</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
                <Label>Name</Label>
                <Input 
                    value={formData.name} 
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    placeholder="Daily Scan"
                />
            </div>
            
            <div className="space-y-2">
                <Label>Frequency (Cron)</Label>
                <div className="flex gap-2">
                    <Input 
                        value={formData.cron_expression} 
                        onChange={(e) => setFormData({...formData, cron_expression: e.target.value})}
                        placeholder="0 3 * * *"
                    />
                    <Select
                        onValueChange={(value) => {
                            if (value) setFormData({...formData, cron_expression: value});
                        }}
                    >
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder="Presets..." />
                        </SelectTrigger>
                        <SelectContent>
                            {presets.map(p => (
                                <SelectItem key={p.cron} value={p.cron}>{p.name}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>
            
            <div className="space-y-2">
                <Label>Scan Type</Label>
                <div className="flex gap-4">
                    {["artwork", "edition", "both"].map((type) => (
                        <label key={type} className="flex items-center gap-2 cursor-pointer">
                            <input 
                                type="radio" 
                                name="scanType"
                                checked={formData.scan_type === type}
                                onChange={() => setFormData({...formData, scan_type: type})}
                            />
                            <span className="capitalize">{type}</span>
                        </label>
                    ))}
                </div>
            </div>
            
            <div className="space-y-2 border-t pt-4">
                <Label>Automation</Label>
                <div className="flex items-center space-x-2">
                    <Checkbox 
                        checked={formData.auto_commit}
                        onCheckedChange={(c) => setFormData({...formData, auto_commit: !!c})}
                    />
                    <span>Automatically apply fixes after scan</span>
                </div>
                
                {formData.auto_commit && (
                    <div className="pl-6 space-y-2 text-sm text-muted-foreground">
                        <div className="flex items-center space-x-2">
                            <Checkbox 
                                checked={formData.auto_commit_skip_unmatched}
                                onCheckedChange={(c) => setFormData({...formData, auto_commit_skip_unmatched: !!c})}
                            />
                            <span>Skip unmatched items (Safer)</span>
                        </div>
                    </div>
                )}
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave}>Save Schedule</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
