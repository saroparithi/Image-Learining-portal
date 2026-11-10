import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function BatchActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({name: '', branch: 'Salem', course: 'Graphic & UX / UI Design', academic_year: '2026', faculty: 'Priya Menon'});
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  if (role !== 'Branch Admin') return null;
  const submit = async event => { event.preventDefault(); setMessage('Creating batch…'); try { await api.createBatch(form); setMessage('Batch created successfully.'); setForm({...form, name: ''}); setOpen(false); } catch (error) { setMessage(error.status === 409 ? 'That batch already exists.' : 'Batch could not be created.'); } };
  return <section className="facultyActionPanel"><div><span className="eyebrow">BATCH ACTION</span><strong>Create a learning cohort</strong><p>Set up a new branch batch and assign its faculty lead.</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Add batch</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Batch name" value={form.name} onChange={e => setForm({...form, name: e.target.value})}/><input required placeholder="Course" value={form.course} onChange={e => setForm({...form, course: e.target.value})}/><input required placeholder="Faculty lead" value={form.faculty} onChange={e => setForm({...form, faculty: e.target.value})}/><button type="submit">Create batch</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
