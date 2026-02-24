'use client';
import AuthGuard from '@/components/layout/AuthGuard';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import type { UserListItem, Role } from '@/types';
import { useState } from 'react';
import { UserPlus, Edit2, Check, X } from 'lucide-react';

const ROLES: Role[] = ['ADMIN', 'AUDITOR', 'APPROVER', 'UPLOADER', 'VIEWER'];

function CreateUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ email: '', password: '', full_name: '', role: 'VIEWER' as string });
  const [error, setError] = useState('');

  const create = useMutation({
    mutationFn: () => api.post('/users', form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); onClose(); setForm({ email: '', password: '', full_name: '', role: 'VIEWER' }); },
    onError: (err: Error) => setError(err.message),
  });

  if (!open) return null;
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="card p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h2 className="text-lg font-bold text-gray-900 mb-4">Create User</h2>
        {error && <div className="mb-3 p-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded">{error}</div>}
        <div className="space-y-3">
          <div><label className="label">Full Name</label><input className="input-field" value={form.full_name} onChange={e => setForm({...form, full_name: e.target.value})} /></div>
          <div><label className="label">Email</label><input type="email" className="input-field" value={form.email} onChange={e => setForm({...form, email: e.target.value})} required /></div>
          <div><label className="label">Password</label><input type="password" className="input-field" value={form.password} onChange={e => setForm({...form, password: e.target.value})} required /></div>
          <div>
            <label className="label">Role</label>
            <select className="input-field" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
              {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button onClick={onClose} className="btn-secondary">Cancel</button>
            <button onClick={() => create.mutate()} disabled={create.isPending} className="btn-primary">{create.isPending ? 'Creating...' : 'Create User'}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function UsersContent() {
  const [showCreate, setShowCreate] = useState(false);
  const qc = useQueryClient();

  const { data: users } = useQuery<UserListItem[]>({ queryKey: ['users'], queryFn: () => api.get('/users') });

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: string }) => api.patch(`/users/${id}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => api.patch(`/users/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Users</h1>
          <p className="text-sm text-gray-500 mt-1">Manage team members and roles</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary"><UserPlus className="w-4 h-4 mr-2" /> Create User</button>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Name</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Email</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Role</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Status</th>
              <th className="text-left text-xs font-medium text-gray-500 uppercase px-4 py-3">Joined</th>
              <th className="text-center text-xs font-medium text-gray-500 uppercase px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!users?.length ? (
              <tr><td colSpan={6} className="text-center py-12 text-gray-400">No users found</td></tr>
            ) : users.map(u => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{u.full_name || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{u.email}</td>
                <td className="px-4 py-3">
                  <select className="text-xs border border-gray-300 rounded px-2 py-1" value={u.role}
                    onChange={e => updateRole.mutate({ id: u.id, role: e.target.value })}>
                    {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${u.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{formatDate(u.created_at)}</td>
                <td className="px-4 py-3 text-center">
                  <button onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                    className={`text-xs px-2 py-1 rounded ${u.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'}`}>
                    {u.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <CreateUserModal open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}

export default function UsersPage() {
  return <AuthGuard><UsersContent /></AuthGuard>;
}
