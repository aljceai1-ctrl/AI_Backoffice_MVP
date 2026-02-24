'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, FileText, Shield, Users, Settings, LogOut, Activity, ClipboardList } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { cn, isAdmin } from '@/lib/utils';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: null },
  { href: '/invoices', label: 'Invoices', icon: FileText, roles: null },
  { href: '/review', label: 'Review Queue', icon: ClipboardList, roles: ['ADMIN', 'APPROVER', 'AUDITOR'] },
  { href: '/audit', label: 'Audit Log', icon: Activity, roles: ['ADMIN', 'AUDITOR', 'APPROVER'] },
  { href: '/admin/users', label: 'Users', icon: Users, roles: ['ADMIN'] },
  { href: '/admin/settings', label: 'Settings', icon: Settings, roles: ['ADMIN'] },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex flex-col z-30">
      <div className="px-6 py-5 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Shield className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-900">AI Backoffice</h1>
            <p className="text-xs text-gray-500 truncate max-w-[160px]">{user?.tenant_name}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.filter(item => !item.roles || (user && item.roles.includes(user.role))).map(item => {
          const active = pathname === item.href || pathname.startsWith(item.href + '/');
          return (
            <Link key={item.href} href={item.href}
              className={cn('flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                active ? 'bg-brand-50 text-brand-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900')}>
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-4 border-t border-gray-100">
        <div className="px-3 py-2 mb-2">
          <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name}</p>
          <p className="text-xs text-gray-500">{user?.role}</p>
        </div>
        <button onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-700 transition-colors">
          <LogOut className="w-5 h-5" /> Sign Out
        </button>
      </div>
    </aside>
  );
}
