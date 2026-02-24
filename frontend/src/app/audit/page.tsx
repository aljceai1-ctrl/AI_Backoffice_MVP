'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDateTime } from '@/lib/utils';
import type { AuditEvent, AuditEffectivenessData } from '@/types';
import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Search } from 'lucide-react';

function AuditContent() {
  const [actionFilter, setActionFilter] = useState('');
  const [page, setPage] = useState(1);

  const { data: events } = useQuery<AuditEvent[]>({
    queryKey: ['audit', actionFilter, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '30' });
      if (actionFilter) params.set('action', actionFilter);
      return api.get(`/audit?${params}`);
    },
  });

  const { data: auditEff } = useQuery<AuditEffectivenessData>({
    queryKey: ['audit-effectiveness'],
    queryFn: () => api.get('/analytics/audit-effectiveness'),
  });

  const actions = ['', 'LOGIN', 'INVOICE_UPLOADED', 'INVOICE_APPROVED', 'INVOICE_REJECTED', 'INVOICE_PAID', 'EMAIL_RECEIVED', 'USER_CREATED'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-sm text-gray-500 mt-1">Track all system activities and user actions</p>
      </div>

      {/* Audit Analytics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-5">
          <p className="text-sm text-gray-500">Total Decisions</p>
          <p className="text-2xl font-bold mt-1">{auditEff?.total_decisions || 0}</p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-gray-500">Rejection Rate</p>
          <p className="text-2xl font-bold mt-1">{auditEff?.rejection_rate || 0}%</p>
          <p className="text-xs text-gray-400">{auditEff?.rejections || 0} rejections</p>
        </div>
        <div className="card p-5">
          <p className="text-sm text-gray-500">Manual vs Auto</p>
          <p className="text-2xl font-bold mt-1">{auditEff?.manual_edits || 0} / {auditEff?.auto_extractions || 0}</p>
          <p className="text-xs text-gray-400">manual edits / auto extractions</p>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Approvals per Approver</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={auditEff?.approvals_per_approver || []}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" fontSize={12} />
            <YAxis fontSize={12} />
            <Tooltip />
            <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Filters */}
      <div className="card p-4 flex items-center gap-3">
        <Activity className="w-4 h-4 text-gray-400" />
        <select className="input-field w-56" value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1); }}>
          <option value="">All Actions</option>
          {actions.filter(Boolean).map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Timestamp</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Action</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Entity</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Actor</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!events?.length ? (
              <tr><td colSpan={5} className="text-center py-12 text-gray-400">No audit events found</td></tr>
            ) : events.map(ev => (
              <tr key={ev.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-xs text-gray-600">{formatDateTime(ev.timestamp)}</td>
                <td className="px-4 py-3"><span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">{ev.action}</span></td>
                <td className="px-4 py-3 text-xs text-gray-600">{ev.entity_type} {ev.entity_id ? `(${ev.entity_id.slice(0, 8)}...)` : ''}</td>
                <td className="px-4 py-3 text-xs text-gray-600">{ev.actor_user_id ? ev.actor_user_id.slice(0, 8) + '...' : 'System'}</td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">{ev.metadata_json ? JSON.stringify(ev.metadata_json) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-gray-200 bg-gray-50">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary py-1 px-3 text-xs">Previous</button>
          <span className="text-xs text-gray-500">Page {page}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={(events?.length || 0) < 30} className="btn-secondary py-1 px-3 text-xs">Next</button>
        </div>
      </div>
    </div>
  );
}

export default function AuditPage() {
  return <AuthGuard><AuditContent /></AuthGuard>;
}
