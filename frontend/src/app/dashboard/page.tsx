'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import type { OverviewData, PaymentAnalytics, EffectivenessData, IngestionData } from '@/types';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, FileText, AlertTriangle, Clock, CheckCircle, DollarSign } from 'lucide-react';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

function KPICard({ label, value, sub, icon: Icon, color }: { label: string; value: string; sub?: string; icon: any; color: string }) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
        </div>
        <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
    </div>
  );
}

function DashboardContent() {
  const { data: overview } = useQuery<OverviewData>({ queryKey: ['overview'], queryFn: () => api.get('/analytics/overview') });
  const { data: payments } = useQuery<PaymentAnalytics>({ queryKey: ['payments-analytics'], queryFn: () => api.get('/analytics/payments') });
  const { data: effectiveness } = useQuery<EffectivenessData>({ queryKey: ['effectiveness'], queryFn: () => api.get('/analytics/effectiveness') });
  const { data: ingestion } = useQuery<IngestionData>({ queryKey: ['ingestion'], queryFn: () => api.get('/analytics/ingestion') });

  const statusData = overview ? Object.entries(overview.by_status).map(([name, value]) => ({ name, value })) : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">Overview of your invoice processing pipeline</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard label="Total Invoices" value={String(overview?.total_invoices || 0)} icon={FileText} color="bg-brand-600" />
        <KPICard label="Total Paid" value={formatCurrency(overview?.total_paid || 0)} icon={DollarSign} color="bg-emerald-600" />
        <KPICard label="Clean Invoice Rate" value={`${overview?.clean_invoice_pct || 0}%`} sub={`${overview?.clean_invoice_count || 0} without exceptions`} icon={CheckCircle} color="bg-green-600" />
        <KPICard label="Avg Approval Time" value={`${effectiveness?.mean_time_to_approval_hours || 0}h`} sub="from creation to approval" icon={Clock} color="bg-orange-500" />
      </div>

      {/* Charts Row 1: Status + Payments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Invoices by Status</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={statusData} cx="50%" cy="50%" outerRadius={100} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                {statusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Payments Over Time</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={payments?.over_time || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tickFormatter={v => v ? new Date(v).toLocaleDateString('en', { month: 'short' }) : ''} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip formatter={(v: number | string) => typeof v === 'number' ? formatCurrency(v) : v} />
              <Bar dataKey="total" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Charts Row 2: Top Vendors + Exception Rate */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Top Vendors by Payment</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={payments?.top_vendors?.slice(0, 8) || []} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" fontSize={12} />
              <YAxis type="category" dataKey="vendor" width={120} fontSize={11} />
              <Tooltip formatter={(v: number | string) => typeof v === 'number' ? formatCurrency(v) : v} />
              <Bar dataKey="total" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Exception Rate Over Time</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={effectiveness?.exception_rate_over_time || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="week" tickFormatter={v => v ? new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' }) : ''} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* System Effectiveness Section */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">System Effectiveness</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <KPICard label="Clean Invoice Rate" value={`${effectiveness?.clean_invoice_pct || 0}%`} icon={CheckCircle} color="bg-green-600" />
          <KPICard label="Avg Time to Approval" value={`${effectiveness?.mean_time_to_approval_hours || 0}h`} icon={Clock} color="bg-blue-600" />
          <KPICard label="Avg Time to Resolve" value={`${effectiveness?.mean_time_to_resolve_hours || 0}h`} icon={AlertTriangle} color="bg-yellow-500" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Top Exception Codes</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={effectiveness?.top_exception_codes || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="code" fontSize={10} angle={-20} textAnchor="end" height={60} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Ingestion: Emails Processed vs Failures</h3>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={ingestion?.daily?.slice(-30) || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="day" tickFormatter={v => v ? new Date(v).toLocaleDateString('en', { day: 'numeric' }) : ''} fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Bar dataKey="processed" fill="#3b82f6" radius={[4, 4, 0, 0]} name="Processed" />
                <Bar dataKey="failures" fill="#ef4444" radius={[4, 4, 0, 0]} name="Failures" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Ingestion Reliability */}
      <div>
        <h2 className="text-lg font-bold text-gray-900 mb-4">Ingestion Reliability</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <KPICard label="Total Emails Processed" value={String(ingestion?.total_processed || 0)} icon={FileText} color="bg-blue-600" />
          <KPICard label="Total Failures" value={String(ingestion?.total_failures || 0)} icon={AlertTriangle} color="bg-red-500" />
          <KPICard label="Overall Failure Rate" value={`${ingestion?.overall_failure_rate || 0}%`} icon={TrendingUp} color="bg-purple-600" />
        </div>
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Retry Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={ingestion?.retry_distribution || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="retries" fontSize={12} label={{ value: 'Retries', position: 'bottom', fontSize: 12 }} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return <AuthGuard><DashboardContent /></AuthGuard>;
}
