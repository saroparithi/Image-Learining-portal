import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function SessionActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({title: '', course: 'Graphic & UX / UI Design', starts_at: '', duration_minutes: '90', type: 'live_class', faculty: 'Priya Menon'});
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  if (!['Faculty', 'Branch Admin'].includes(role)) return null;
  const submit = async event => {
    event.preventDefault(); setMessage('Scheduling session…');
    try { await api.createSession({...form, duration_minutes: Number(form.duration_minutes)}); setMessage('Live session scheduled successfully.'); setForm({...form, title: '', starts_at: ''}); setOpen(false); }
    catch (error) { setMessage(error.status === 403 ? 'You do not have permission to schedule sessions.' : 'Session could not be scheduled.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">SESSION ACTION</span><strong>Schedule a live class</strong><p>Coordinate a live session for your branch learners.</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Schedule session</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Session title" value={form.title} onChange={e => setForm({...form, title: e.target.value})}/><input required type="datetime-local" value={form.starts_at} onChange={e => setForm({...form, starts_at: e.target.value})}/><input required type="number" min="15" max="480" placeholder="Duration (minutes)" value={form.duration_minutes} onChange={e => setForm({...form, duration_minutes: e.target.value})}/><button type="submit">Schedule session</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
