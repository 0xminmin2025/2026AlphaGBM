import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/components/auth/AuthProvider';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog';
import { Key, Plus, Trash2, Power, Copy, Check, AlertTriangle, Terminal, Code2, ExternalLink } from 'lucide-react';
import api from '@/lib/api';
import { useToastHelpers } from '@/components/ui/toast';

interface ApiKeyItem {
  id: number;
  name: string;
  prefix: string;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

export default function ApiKeys() {
  const { user } = useAuth();
  const toast = useToastHelpers();
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  // Delete confirm
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await api.get('/keys');
      setKeys(res.data.keys);
    } catch {
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    if (user) fetchKeys();
  }, [user, fetchKeys]);

  const handleCreate = async () => {
    setCreating(true);
    try {
      const res = await api.post('/keys', { name: newKeyName || 'Default' });
      setCreatedKey(res.data.key);
      fetchKeys();
    } catch (err: any) {
      toast.error(err.response?.data?.error || 'Failed to create key');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/keys/${id}`);
      setKeys(prev => prev.filter(k => k.id !== id));
      setDeleteId(null);
      toast.success('API Key deleted');
    } catch {
      toast.error('Failed to delete key');
    }
  };

  const handleToggle = async (id: number) => {
    try {
      const res = await api.post(`/keys/${id}/toggle`);
      setKeys(prev => prev.map(k => k.id === id ? { ...k, is_active: res.data.is_active } : k));
    } catch {
      toast.error('Failed to toggle key');
    }
  };

  const handleCopy = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const closeCreateModal = () => {
    setCreateOpen(false);
    setCreatedKey(null);
    setNewKeyName('');
    setCopied(false);
  };

  if (!user) return (
    <div className="flex items-center justify-center min-h-[50vh] text-slate-400">
      Please log in
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-3">
            <Key className="w-7 h-7 text-[#0D9B97]" />
            API Key Management
          </h1>
          <p className="text-slate-400 mt-2 text-sm">
            Use API Keys to access AlphaGBM analysis from OpenClaw, Claude Desktop, or your own applications.
          </p>
        </div>
        <Button
          onClick={() => setCreateOpen(true)}
          className="bg-[#0D9B97] hover:bg-[#0D9B97]/80 text-white shrink-0"
        >
          <Plus className="w-4 h-4 mr-2" /> Create Key
        </Button>
      </div>

      {/* Key List */}
      <div className="space-y-3">
        {loading ? (
          <Card className="bg-[#0f0f11] border-white/10">
            <CardContent className="py-12 text-center text-slate-500">Loading...</CardContent>
          </Card>
        ) : keys.length === 0 ? (
          <Card className="bg-[#0f0f11] border-white/10">
            <CardContent className="py-12 text-center text-slate-500">
              No API keys yet. Create one to get started.
            </CardContent>
          </Card>
        ) : (
          keys.map(k => (
            <Card key={k.id} className="bg-[#0f0f11] border-white/10">
              <CardContent className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-4">
                <div className="flex items-center gap-4 min-w-0">
                  <div className={`w-2.5 h-2.5 rounded-full shrink-0 ${k.is_active ? 'bg-emerald-500' : 'bg-slate-600'}`} />
                  <div className="min-w-0">
                    <div className="font-medium truncate">{k.name}</div>
                    <div className="text-sm text-slate-500 font-mono">{k.prefix}••••••••</div>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-sm text-slate-500 shrink-0">
                  <div className="hidden sm:block">
                    <span className="text-slate-600">Created </span>
                    {new Date(k.created_at).toLocaleDateString()}
                  </div>
                  <div className="hidden sm:block">
                    <span className="text-slate-600">Last used </span>
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggle(k.id)}
                      className={k.is_active ? 'text-amber-500 hover:text-amber-400' : 'text-emerald-500 hover:text-emerald-400'}
                    >
                      <Power className="w-4 h-4 mr-1" />
                      {k.is_active ? 'Disable' : 'Enable'}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteId(k.id)}
                      className="text-red-500 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Quick Start Guide */}
      <Card className="bg-[#0f0f11] border-white/10">
        <CardHeader>
          <CardTitle className="text-lg">Quick Start</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-6 md:grid-cols-2">
            {/* OpenClaw */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-[#0D9B97] font-medium">
                <Terminal className="w-4 h-4" /> OpenClaw / MCP
              </div>
              <div className="space-y-2 text-sm">
                <div className="bg-[#1a1a2e] rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto">
                  <div className="text-slate-500"># Set environment variable</div>
                  <div>export ALPHAGBM_API_KEY="agbm_your_key"</div>
                </div>
                <div className="bg-[#1a1a2e] rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto">
                  <div className="text-slate-500"># Use in OpenClaw</div>
                  <div>"Analyze TSLA options for April expiry"</div>
                </div>
              </div>
            </div>
            {/* API Developer */}
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-[#0D9B97] font-medium">
                <Code2 className="w-4 h-4" /> API Developer
              </div>
              <div className="bg-[#1a1a2e] rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto">
                <div className="text-slate-500"># Stock analysis</div>
                <div>curl -X POST https://alphagbm.com/api/stock/analyze-async \</div>
                <div className="pl-4">-H "Authorization: Bearer $ALPHAGBM_API_KEY" \</div>
                <div className="pl-4">-H "Content-Type: application/json" \</div>
                <div className="pl-4">{`-d '{"ticker":"TSLA","style":"balanced"}'`}</div>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-white/5 text-center">
            <a
              href="/api/docs/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-[#0D9B97] hover:text-[#0D9B97]/80 inline-flex items-center gap-1"
            >
              Full API Documentation <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Create Modal */}
      <Dialog open={createOpen} onOpenChange={closeCreateModal}>
        <DialogContent className="bg-[#1a1a2e] border-white/10">
          <DialogHeader>
            <DialogTitle>{createdKey ? 'API Key Created' : 'Create New API Key'}</DialogTitle>
            <DialogDescription>
              {createdKey
                ? 'Save this key now. You won\'t be able to see it again.'
                : 'Give your API key a name to identify it later.'}
            </DialogDescription>
          </DialogHeader>

          {createdKey ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                <span className="text-xs text-amber-400">
                  This is the only time the full key will be shown. Copy it now.
                </span>
              </div>
              <div className="flex gap-2">
                <code className="flex-1 bg-[#0f0f11] p-3 rounded-lg font-mono text-sm text-[#0D9B97] break-all">
                  {createdKey}
                </code>
                <Button variant="outline" size="sm" onClick={handleCopy} className="shrink-0">
                  {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
                </Button>
              </div>
              <DialogFooter>
                <Button onClick={closeCreateModal} className="bg-[#0D9B97] hover:bg-[#0D9B97]/80">
                  Done
                </Button>
              </DialogFooter>
            </div>
          ) : (
            <div className="space-y-4">
              <Input
                placeholder="e.g. My Laptop, Production Server"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                className="bg-[#0f0f11] border-white/10"
                onKeyDown={e => e.key === 'Enter' && handleCreate()}
              />
              <DialogFooter>
                <Button variant="ghost" onClick={closeCreateModal}>Cancel</Button>
                <Button
                  onClick={handleCreate}
                  disabled={creating}
                  className="bg-[#0D9B97] hover:bg-[#0D9B97]/80"
                >
                  {creating ? 'Creating...' : 'Create'}
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="bg-[#1a1a2e] border-white/10">
          <DialogHeader>
            <DialogTitle>Delete API Key</DialogTitle>
            <DialogDescription>
              This action cannot be undone. Any applications using this key will lose access.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button
              variant="destructive"
              onClick={() => deleteId && handleDelete(deleteId)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
