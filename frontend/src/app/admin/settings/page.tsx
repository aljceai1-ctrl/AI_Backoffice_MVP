'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { TenantSettings } from '@/types';
import { useState, useEffect } from 'react';
import { Settings, Save, Mail } from 'lucide-react';

function SettingsContent() {
  const qc = useQueryClient();
  const { data: settings } = useQuery<TenantSettings>({ queryKey: ['settings'], queryFn: () => api.get('/tenants/settings') });
  const [name, setName] = useState('');
  const [currencies, setCurrencies] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) {
      setName(settings.name);
      setCurrencies(settings.allowed_currencies);
    }
  }, [settings]);

  const update = useMutation({
    mutationFn: () => api.patch('/tenants/settings', { name, allowed_currencies: currencies }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['settings'] }); setSaved(true); setTimeout(() => setSaved(false), 2000); },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Configure your tenant settings</p>
      </div>

      <div className="card p-6 max-w-2xl">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2"><Settings className="w-4 h-4" /> Company Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="label">Company Name</label>
            <input className="input-field" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Allowed Currencies (comma-separated)</label>
            <input className="input-field" value={currencies} onChange={e => setCurrencies(e.target.value)} placeholder="AED,USD,EUR,GBP" />
          </div>
          <button onClick={() => update.mutate()} disabled={update.isPending} className="btn-primary">
            <Save className="w-4 h-4 mr-2" /> {update.isPending ? 'Saving...' : 'Save Settings'}
          </button>
          {saved && <p className="text-sm text-green-600">Settings saved!</p>}
        </div>
      </div>

      <div className="card p-6 max-w-2xl">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2"><Mail className="w-4 h-4" /> Email Ingestion</h3>
        <div className="space-y-3">
          <div>
            <label className="label">Inbound Email Address</label>
            <div className="flex items-center gap-2">
              <code className="px-3 py-2 bg-gray-100 rounded-lg text-sm font-mono">{settings?.inbound_email_alias}@inbound.local</code>
              <span className="text-xs text-gray-500">(MailHog local dev)</span>
            </div>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-700">
              <strong>How to test:</strong> Send an email with PDF attachments to the address above using MailHog (http://localhost:8025).
              The system polls for new emails every 15 seconds and automatically creates invoice records from attachments.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return <AuthGuard><SettingsContent /></AuthGuard>;
}
