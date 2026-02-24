'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatCurrency, formatDate, formatDateTime, statusColor, canApprove } from '@/lib/utils';
import type { InvoiceListResponse } from '@/types';
import { useState } from 'react';
import Link from 'next/link';
import { ClipboardList, Mail, Upload, ChevronLeft, ChevronRight, AlertCircle } from 'lucide-react';

function ReviewQueueContent() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [sourceFilter, setSourceFilter] = useState('');

  const { data, isLoading } = useQuery<InvoiceListResponse>({
    queryKey: ['review-queue', page, sourceFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (sourceFilter) params.set('source', sourceFilter);
      return api.get(`/invoices/review-queue?${params}`);
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            {data?.total || 0} invoice{(data?.total || 0) !== 1 ? 's' : ''} awaiting review
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap gap-3">
        <select
          className="input-field w-48"
          value={sourceFilter}
          onChange={e => { setSourceFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Sources</option>
          <option value="EMAIL">Email Ingested</option>
          <option value="UPLOAD">Manual Upload</option>
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Invoice</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Source</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">From / Vendor</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase px-4 py-3">Amount</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Status</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Errors</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Received</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">Loading...</td></tr>
            ) : !data?.items?.length ? (
              <tr>
                <td colSpan={7} className="text-center py-12">
                  <ClipboardList className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 font-medium">No invoices to review</p>
                  <p className="text-sm text-gray-400 mt-1">All caught up! New invoices from email or uploads will appear here.</p>
                </td>
              </tr>
            ) : data.items.map(inv => (
              <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <Link href={`/invoices/${inv.id}`} className="text-sm font-medium text-brand-600 hover:text-brand-700">
                    {inv.invoice_number || inv.original_filename || 'Untitled'}
                  </Link>
                  {inv.email_subject && (
                    <p className="text-xs text-gray-400 truncate max-w-[200px]">{inv.email_subject}</p>
                  )}
                </td>
                <td className="px-4 py-3">
                  {inv.source === 'EMAIL' ? (
                    <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                      <Mail className="w-3 h-3" /> Email
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                      <Upload className="w-3 h-3" /> Upload
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">
                  {inv.source === 'EMAIL' ? (inv.email_from || '—') : (inv.vendor || '—')}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
                  {formatCurrency(inv.amount, inv.currency)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(inv.status)}`}>
                    {inv.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  {inv.exceptions.length > 0 ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">
                      <AlertCircle className="w-3 h-3" />{inv.exceptions.length}
                    </span>
                  ) : <span className="text-xs text-gray-400">—</span>}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{formatDateTime(inv.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <p className="text-xs text-gray-500">Page {data.page} of {Math.ceil(data.total / data.page_size)}</p>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary py-1 px-2">
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button onClick={() => setPage(p => p + 1)} disabled={page * 20 >= data.total} className="btn-secondary py-1 px-2">
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReviewQueuePage() {
  return <AuthGuard><ReviewQueueContent /></AuthGuard>;
}
