export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
}

export interface UserListItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  tenant_id: string;
  created_at: string;
}

export interface InvoiceException {
  id: string;
  code: string;
  message: string;
  severity: string;
  created_at: string;
  resolved_at: string | null;
}

export interface ApprovalRecord {
  id: string;
  decided_by_user_id: string;
  decision: string;
  decided_at: string;
  notes: string;
}

export interface PaymentBrief {
  id: string;
  paid_amount: number;
  paid_currency: string;
  paid_at: string;
  payment_method: string;
  reference: string;
}

export interface Invoice {
  id: string;
  tenant_id: string;
  vendor: string;
  invoice_number: string;
  invoice_date: string | null;
  amount: number | null;
  currency: string;
  status: string;
  source: string;
  original_filename: string;
  email_subject: string | null;
  email_from: string | null;
  attachment_count: number;
  created_at: string;
  updated_at: string;
  exceptions: InvoiceException[];
  approvals: ApprovalRecord[];
  payments: PaymentBrief[];
}

export interface InvoiceListResponse {
  items: Invoice[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditEvent {
  id: string;
  tenant_id: string;
  timestamp: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  metadata_json: Record<string, unknown> | null;
}

export interface OverviewData {
  total_invoices: number;
  by_status: Record<string, number>;
  total_paid: number;
  total_exceptions: number;
  clean_invoice_count: number;
  clean_invoice_pct: number;
}

export interface PaymentAnalytics {
  over_time: { month: string; total: number; count: number }[];
  top_vendors: { vendor: string; total: number; count: number }[];
}

export interface EffectivenessData {
  exception_rate_over_time: { week: string; count: number }[];
  top_exception_codes: { code: string; count: number }[];
  mean_time_to_approval_hours: number;
  mean_time_to_resolve_hours: number;
  clean_invoice_pct: number;
  total_invoices_in_range: number;
}

export interface IngestionData {
  daily: { day: string; processed: number; failures: number; retries: number; failure_rate: number }[];
  retry_distribution: { retries: number; count: number }[];
  total_processed: number;
  total_failures: number;
  overall_failure_rate: number;
}

export interface AuditEffectivenessData {
  approvals_per_approver: { user_id: string; name: string; count: number }[];
  total_decisions: number;
  rejections: number;
  rejection_rate: number;
  manual_edits: number;
  auto_extractions: number;
}

export interface TenantSettings {
  id: string;
  name: string;
  inbound_email_alias: string;
  allowed_currencies: string;
  created_at: string;
}

export type Role = 'ADMIN' | 'AUDITOR' | 'APPROVER' | 'UPLOADER' | 'VIEWER';
