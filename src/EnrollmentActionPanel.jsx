import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function EnrollmentActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview');
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [students, setStudents] = useState([]);
  const [batches, setBatches] = useState([]);
  const [form, setForm] = useState({student_id: '', batch_id: '', course: '', branch: 'Salem'});
  useEffect(() => { const sync = () => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }; const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Branch Admin' || section !== 'Students') return; const token = localStorage.getItem('image-lms-token'); if (token) Promise.all([api.students(token), api.batches(token)]).then(([studentResult, batchResult]) => { setStudents(studentResult.items || []); setBatches(batchResult.items || []); }).catch(() => { setStudents([]); setBatches([]); }); }, [role, section]);
  if (role !== 'Branch Admin' || section !== 'Students') return null;
  const submit = async event => {
    event.preventDefault(); setMessage('Enrolling student…');
    try { const result = await api.createEnrollment(form); setMessage(`${result.enrollment?.student_name || form.student_id} enrolled successfully.`); setForm({...form, student_id: ''}); setOpen(false); }
    catch (error) { setMessage(error.status === 409 ? 'Student is already enrolled in this batch.' : error.status === 403 ? 'You cannot enroll outside your branch.' : 'Enrollment could not be created.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">ENROLLMENT ACTION</span><strong>Assign a student to a batch</strong><p>Connect a Salem learner to the correct course and delivery batch.</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Enroll student</button>{open && <form className="workspaceForm" onSubmit={submit}><select required value={form.student_id} onChange={e => setForm({...form, student_id: e.target.value})}><option value="">Choose student</option>{students.map(student => <option key={student.id} value={student.id}>{student.name} · {student.email}</option>)}</select><select required value={form.batch_id} onChange={e => { const batch = batches.find(item => item.id === e.target.value); setForm({...form, batch_id: e.target.value, course: batch?.course || form.course}); }}><option value="">Choose batch</option>{batches.map(batch => <option key={batch.id} value={batch.id}>{batch.name} · {batch.course}</option>)}</select><input required placeholder="Course" value={form.course} onChange={e => setForm({...form, course: e.target.value})}/><button type="submit">Create enrollment</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
