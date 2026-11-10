import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultyStudentPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [students, setStudents] = useState([]); const [query, setQuery] = useState('');
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'Students') return; const token = localStorage.getItem('image-lms-token'); if (token) api.students(token).then(result => setStudents(result.items || [])).catch(() => setStudents([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'Students') return null;
  const visible = students.filter(item => `${item.name} ${item.email} ${item.course} ${item.branch}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="roleWorkspace facultyClasses"><div className="roleWorkspaceHead"><div><span className="eyebrow">FACULTY PORTAL</span><h2>Student roster</h2><p>Find learners assigned to your campus and courses.</p></div><div className="workspaceActions"><input aria-label="Search students" placeholder="Search students..." value={query} onChange={event => setQuery(event.target.value)}/><span className="workspaceCount">{visible.length} students</span></div></div>{visible.length ? <div className="classGrid">{visible.map((item, index) => <article className="classCard" key={item.id || index}><span>{item.status || 'Active learner'}</span><strong>{item.name || 'Student'}</strong><p>{item.course || 'Course not assigned'}</p><small>{item.branch || 'Campus pending'} · {item.email || 'Email unavailable'}</small></article>)}</div> : <p className="emptyState">No students match your search.</p>}</section>;
}
