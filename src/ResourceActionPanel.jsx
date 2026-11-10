import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function ResourceActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({title: '', type: 'pdf', course: 'Graphic & UX / UI Design', resource_url: ''});
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  if (!['Faculty', 'Branch Admin'].includes(role)) return null;
  const submit = async event => {
    event.preventDefault(); setMessage('Submitting resource…');
    try { await api.createResource(form); setMessage('Resource submitted for approval.'); setForm({...form, title: '', resource_url: ''}); setOpen(false); }
    catch (error) { setMessage(error.status === 403 ? 'You do not have permission to publish resources.' : 'Resource could not be submitted.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">RESOURCE ACTION</span><strong>Share a learning resource</strong><p>Submit a file or link for your learners and the approval queue.</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Add resource</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Resource title" value={form.title} onChange={e => setForm({...form, title: e.target.value})}/><select value={form.type} onChange={e => setForm({...form, type: e.target.value})}><option value="pdf">PDF</option><option value="video">Video</option><option value="link">Link</option></select><input required type="url" placeholder="Resource URL" value={form.resource_url} onChange={e => setForm({...form, resource_url: e.target.value})}/><button type="submit">Submit resource</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
