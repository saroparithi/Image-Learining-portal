import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function FacultyAdminActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({name: '', email: '', branch: 'Salem', specialization: ''});
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  if (role !== 'Branch Admin') return null;
  const submit = async event => {
    event.preventDefault(); setMessage('Adding faculty…');
    try { const result = await api.createFaculty(form); setMessage(`${result.faculty?.name || form.name} added successfully.`); setForm({name: '', email: '', branch: 'Salem', specialization: ''}); setOpen(false); }
    catch (error) { setMessage(error.status === 403 ? 'You do not have permission to add faculty.' : 'Faculty could not be added.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">FACULTY ACTION</span><strong>Onboard a faculty member</strong><p>Add a mentor to the Salem branch faculty roster.</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Add faculty</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Full name" value={form.name} onChange={e => setForm({...form, name: e.target.value})}/><input required type="email" placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})}/><input required placeholder="Specialization" value={form.specialization} onChange={e => setForm({...form, specialization: e.target.value})}/><button type="submit">Add faculty</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
