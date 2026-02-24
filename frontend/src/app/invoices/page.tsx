'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatCurrency, formatDate, statusColor, canUpload } from '@/lib/utils';
import type { InvoiceListResponse } from '@/types';
import { useState } from 'react';
import Link from 'next/link';
import { Upload, Search, ChevronLeft, ChevronRight } from 'lucide-react';

function UploadModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [formData, setFormData] = useState({ vendor: '', invoice_number: '', invoice_date: '', amount: '', currency: 'AED' });
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const fd = new FormData();
    fd.append('file', file);
    Object.entries(formData).forEach(([k, v]) => fd.append(k, v));
    try {
      await api.upload('/invoices/upload', fd);
      qc.invalidateQueries({ queryKey: ['invoices'] });
      onClose();
      setFormData({ vendor: '', invoice_number: '', invoice_date: '', amount: '', currency: 'AED' });
      setFile(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="card p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-gray-900 mb-4">Upload Invoice</h2>
        <div className="space-y-3">
          <div>
            <label className="label">File (PDF/Image)</label>
            <input type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={e => setFile(e.target.files?.[0] || null)} className="input-field" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="label">Vendor</label><input className="input-field" value={formData.vendor} onChange={e => setFormData({...formData, vendor: e.target.value})} /></div>
            <div><label className="label">Invoice #</label><input className="input-field" value={formData.invoice_number} onChange={e => setFormData({...formData, invoice_number: e.target.value})} /></div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div><label className="label">Date</label><input type="date" className="input-field" value={formData.invoice_date} onChange={e => setFormData({...formData, invoice_date: e.target.value})} /></div>
            <div><label className="label">Amount</label><input type="number" step="0.01" className="input-field" value={formData.amount} onChange={e => setFormData({...formData, amount: e.target.value})} /></div>
            <div><label className="label">Currency</label>
              <select className="input-field" value={formData.currency} onChange={e => setFormData({...formData, currency: e.target.value})}>
                <option>AED</option><option>USD</option><option>EUR</option><option>GBP</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={onClose} className="btn-secondary">Cancel</button>
            <button onClick={handleUpload} disabled={!file || uploading} className="btn-primary">{uploading ? 'Uploading...' : 'Upload'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function InvoicesContent() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');
  const [showUpload, setShowUpload] = useState(false);

  const { data, isLoading } = useQuery<InvoiceListResponse>({
    queryKey: ['invoices', page, statusFilter, vendorFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (statusFilter) params.set('status_filter', statusFilter);
      if (vendorFilter) params.set('vendor', vendorFilter);
      return api.get(`/invoices?${params}`);
    },
  });

  const statuses = ['', 'NEW', 'VALIDATED', 'APPROVAL_PENDING', 'APPROVED', 'REJECTED', 'PAID'];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">{data?.total || 0} total invoices</p>
        </div>
        {user && canUpload(user.role) && (
          <button onClick={() => setShowUpload(true)} className="btn-primary"><Upload className="w-4 h-4 mr-2" /> Upload Invoice</button>
        )}
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-gray-400" />
          <input placeholder="Search vendor..." className="input-field w-48" value={vendorFilter} onChange={e => { setVendorFilter(e.target.value); setPage(1); }} />
        </div>
        <select className="input-field w-48" value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          {statuses.filter(Boolean).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Invoice</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Vendor</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Date</th>
              <th className="text-right text-xs font-medium text-gray-500 uppercase px-4 py-3">Amount</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Status</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Source</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Errors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">Loading...</td></tr>
            ) : !data?.items?.length ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">No invoices found</td></tr>
            ) : data.items.map(inv => (
              <tr key={inv.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  <Link href={`/invoices/${inv.id}`} className="text-sm font-medium text-brand-600 hover:text-brand-700">
                    {inv.invoice_number || 'No number'}
                  </Link>
                  <p className="text-xs text-gray-400">{inv.original_filename}</p>
                </td>
                <td className="px-4 py-3 text-sm text-gray-700">{inv.vendor || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{formatDate(inv.invoice_date)}</td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">{formatCurrency(inv.amount, inv.currency)}</td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${statusColor(inv.status)}`}>{inv.status}</span>
                </td>
                <td className="px-4 py-3 text-center text-xs text-gray-500">{inv.source}</td>
                <td className="px-4 py-3 text-center">
                  {inv.exceptions.length > 0 ? (
                    <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">{inv.exceptions.length}</span>
                  ) : <span className="text-xs text-gray-400">—</span>}
                </td>
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

      <UploadModal open={showUpload} onClose={() => setShowUpload(false)} />
    </div>
  );
}

export default function InvoicesPage() {
  return <AuthGuard><InvoicesContent /></AuthGuard>;
}
