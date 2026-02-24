'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { formatCurrency, formatDate, formatDateTime, statusColor, canApprove } from '@/lib/utils';
import type { Invoice } from '@/types';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Download, Check, X, DollarSign, AlertCircle, FileText, Clock, User } from 'lucide-react';

function InvoiceDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: inv, isLoading } = useQuery<Invoice>({
    queryKey: ['invoice', id],
    queryFn: () => api.get(`/invoices/${id}`),
  });

  const approve = useMutation({
    mutationFn: () => api.post(`/invoices/${id}/approve`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoice', id] }); qc.invalidateQueries({ queryKey: ['invoices'] }); },
  });

  const reject = useMutation({
    mutationFn: () => api.post(`/invoices/${id}/reject`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoice', id] }); qc.invalidateQueries({ queryKey: ['invoices'] }); },
  });

  const markPaid = useMutation({
    mutationFn: () => api.post(`/invoices/${id}/mark-paid`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoice', id] }); qc.invalidateQueries({ queryKey: ['invoices'] }); },
  });

  if (isLoading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" /></div>;
  if (!inv) return <div className="text-center py-12 text-gray-500">Invoice not found</div>;

  const canAct = user && canApprove(user.role);
  const canApproveThis = canAct && ['APPROVAL_PENDING', 'VALIDATED'].includes(inv.status);
  const canPayThis = canAct && inv.status === 'APPROVED';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="btn-secondary py-1.5 px-2"><ArrowLeft className="w-4 h-4" /></button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{inv.invoice_number || 'Invoice'}</h1>
          <p className="text-sm text-gray-500">{inv.vendor} &middot; {formatDate(inv.invoice_date)}</p>
        </div>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${statusColor(inv.status)}`}>{inv.status}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Invoice Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div><p className="text-xs text-gray-500">Amount</p><p className="text-lg font-bold">{formatCurrency(inv.amount, inv.currency)}</p></div>
              <div><p className="text-xs text-gray-500">Currency</p><p className="text-sm font-medium">{inv.currency}</p></div>
              <div><p className="text-xs text-gray-500">Source</p><p className="text-sm font-medium">{inv.source}</p></div>
              <div><p className="text-xs text-gray-500">File</p><p className="text-sm">{inv.original_filename || '—'}</p></div>
              <div><p className="text-xs text-gray-500">Created</p><p className="text-sm">{formatDateTime(inv.created_at)}</p></div>
              <div><p className="text-xs text-gray-500">Updated</p><p className="text-sm">{formatDateTime(inv.updated_at)}</p></div>
            </div>
            {inv.original_filename && (
              <a href={`/api/invoices/${inv.id}/download`} className="btn-secondary mt-4 inline-flex"><Download className="w-4 h-4 mr-2" /> Download File</a>
            )}
          </div>

          {/* Exceptions */}
          {inv.exceptions.length > 0 && (
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2"><AlertCircle className="w-4 h-4 text-red-500" /> Validation Exceptions ({inv.exceptions.length})</h3>
              <div className="space-y-2">
                {inv.exceptions.map(exc => (
                  <div key={exc.id} className={`p-3 rounded-lg border ${exc.severity === 'ERROR' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <span className={`text-xs font-medium ${exc.severity === 'ERROR' ? 'text-red-700' : 'text-yellow-700'}`}>{exc.code}</span>
                        <p className="text-sm text-gray-700 mt-0.5">{exc.message}</p>
                      </div>
                      {exc.resolved_at && <span className="text-xs text-green-600 font-medium">Resolved</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Payments */}
          {inv.payments.length > 0 && (
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2"><DollarSign className="w-4 h-4 text-emerald-500" /> Payments</h3>
              {inv.payments.map(p => (
                <div key={p.id} className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                  <div><p className="text-sm font-medium">{formatCurrency(p.paid_amount, p.paid_currency)}</p><p className="text-xs text-gray-500">{p.payment_method} &middot; {p.reference}</p></div>
                  <p className="text-xs text-gray-500">{formatDateTime(p.paid_at)}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar: Actions + History */}
        <div className="space-y-6">
          {(canApproveThis || canPayThis) && (
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Actions</h3>
              <div className="space-y-2">
                {canApproveThis && (
                  <>
                    <button onClick={() => approve.mutate()} disabled={approve.isPending} className="btn-primary w-full"><Check className="w-4 h-4 mr-2" /> Approve</button>
                    <button onClick={() => reject.mutate()} disabled={reject.isPending} className="btn-danger w-full"><X className="w-4 h-4 mr-2" /> Reject</button>
                  </>
                )}
                {canPayThis && (
                  <button onClick={() => markPaid.mutate()} disabled={markPaid.isPending} className="btn-primary w-full bg-emerald-600 hover:bg-emerald-700"><DollarSign className="w-4 h-4 mr-2" /> Mark as Paid</button>
                )}
              </div>
            </div>
          )}

          {/* Approval History */}
          {inv.approvals.length > 0 && (
            <div className="card p-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Approval History</h3>
              <div className="space-y-3">
                {inv.approvals.map(a => (
                  <div key={a.id} className="flex items-start gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center ${a.decision === 'APPROVED' ? 'bg-green-100' : 'bg-red-100'}`}>
                      {a.decision === 'APPROVED' ? <Check className="w-3 h-3 text-green-700" /> : <X className="w-3 h-3 text-red-700" />}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{a.decision}</p>
                      <p className="text-xs text-gray-500">{formatDateTime(a.decided_at)}</p>
                      {a.notes && <p className="text-xs text-gray-600 mt-1">{a.notes}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InvoiceDetailPage() {
  return <AuthGuard><InvoiceDetail /></AuthGuard>;
}
