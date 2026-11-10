import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultySchedulePanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [sessions, setSessions] = useState([]);
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'Schedule') return; const token = localStorage.getItem('image-lms-token'); if (token) api.sessions(token).then(result => setSessions(result.items || [])).catch(() => setSessions([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'Schedule') return null;
  return <section className="roleWorkspace facultyClasses"><div className="roleWorkspaceHead"><div><span className="eyebrow">FACULTY PORTAL</span><h2>Teaching schedule</h2><p>Upcoming live classes, workshops, and mentor sessions.</p></div><span className="workspaceCount">{sessions.length} sessions</span></div>{sessions.length ? <div className="classGrid">{sessions.map((item, index) => <article className="classCard" key={item.id || index}><span>{item.type || 'Live session'}</span><strong>{item.title}</strong><p>{item.course || 'IMAGE programme'}</p><small>{item.starts_at ? new Date(item.starts_at).toLocaleString() : 'Schedule pending'} · {item.duration_minutes || 90} minutes</small></article>)}</div> : <p className="emptyState">No upcoming sessions are scheduled.</p>}</section>;
}
