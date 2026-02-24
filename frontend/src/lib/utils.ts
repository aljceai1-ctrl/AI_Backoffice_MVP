import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number | null, currency: string = 'AED'): string {
  if (amount === null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 2 }).format(amount);
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return dateStr;
  }
}

const STATUS_COLORS: Record<string, string> = {
  NEW: 'bg-gray-100 text-gray-700',
  EXTRACTED: 'bg-blue-100 text-blue-700',
  VALIDATED: 'bg-yellow-100 text-yellow-700',
  APPROVAL_PENDING: 'bg-orange-100 text-orange-700',
  APPROVED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  PAID: 'bg-emerald-100 text-emerald-800',
};

export function statusColor(status: string): string {
  return STATUS_COLORS[status] || 'bg-gray-100 text-gray-700';
}

export function canApprove(role: string): boolean {
  return ['ADMIN', 'APPROVER'].includes(role);
}

export function canUpload(role: string): boolean {
  return ['ADMIN', 'APPROVER', 'UPLOADER'].includes(role);
}

export function isAdmin(role: string): boolean {
  return role === 'ADMIN';
}
