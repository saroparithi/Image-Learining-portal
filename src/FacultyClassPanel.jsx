import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultyClassPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [classes, setClasses] = useState([]); const [query, setQuery] = useState('');
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'My classes') return; const token = localStorage.getItem('image-lms-token'); if (token) api.facultyClasses(token).then(result => setClasses(result.items || [])).catch(() => setClasses([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'My classes') return null;
  const visible = classes.filter(item => `${item.title} ${item.course} ${item.branch} ${item.faculty}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="roleWorkspace facultyClasses"><div className="roleWorkspaceHead"><div><span className="eyebrow">FACULTY PORTAL</span><h2>My assigned classes</h2><p>Manage your upcoming teaching sessions and class delivery.</p></div><div className="workspaceActions"><input aria-label="Search classes" placeholder="Search classes..." value={query} onChange={event => setQuery(event.target.value)}/><span className="workspaceCount">{visible.length} classes</span></div></div>{visible.length ? <div className="classGrid">{visible.map((item, index) => <article className="classCard" key={item.id || index}><span>{item.type || 'Class session'}</span><strong>{item.title || item.name || item.course || 'Assigned class'}</strong><p>{item.course || 'IMAGE programme'}</p><small>{item.branch || 'Assigned campus'} · {item.starts_at ? new Date(item.starts_at).toLocaleString() : 'Schedule pending'}</small></article>)}</div> : <p className="emptyState">No assigned classes match your search.</p>}</section>;
}
