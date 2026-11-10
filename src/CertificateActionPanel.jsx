import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function CertificateActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({student_id: 'stu-1001', student_name: 'Arjun Kumar', course: 'Motion Design'});
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  if (!['Branch Admin', 'Management'].includes(role)) return null;
  const submit = async event => {
    event.preventDefault();
    setMessage('Issuing certificate…');
    try { const result = await api.issueCertificate(form); setMessage(`Certificate ${result.certificate?.id || 'issued'} successfully.`); setOpen(false); }
    catch (error) { setMessage(error.status === 403 ? 'You do not have permission to issue certificates.' : 'Certificate could not be issued.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">CERTIFICATION ACTION</span><strong>Issue a course certificate</strong><p>{role === 'Management' ? 'Recognize a learner across the IMAGE network.' : 'Recognize a learner who has completed the branch programme.'}</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Issue certificate</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Student ID" value={form.student_id} onChange={e => setForm({...form, student_id: e.target.value})}/><input required placeholder="Student name" value={form.student_name} onChange={e => setForm({...form, student_name: e.target.value})}/><input required placeholder="Course" value={form.course} onChange={e => setForm({...form, course: e.target.value})}/><button type="submit">Issue certificate</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
