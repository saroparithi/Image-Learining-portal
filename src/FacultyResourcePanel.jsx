import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultyResourcePanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [resources, setResources] = useState([]); const [query, setQuery] = useState('');
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'Resources') return; const token = localStorage.getItem('image-lms-token'); if (token) api.resources(token).then(result => setResources(result.items || [])).catch(() => setResources([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'Resources') return null;
  const visible = resources.filter(item => `${item.title} ${item.course} ${item.type} ${item.status}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="roleWorkspace facultyClasses"><div className="roleWorkspaceHead"><div><span className="eyebrow">FACULTY PORTAL</span><h2>Teaching resources</h2><p>Find resources available for your classes and learners.</p></div><div className="workspaceActions"><input aria-label="Search resources" placeholder="Search resources..." value={query} onChange={event => setQuery(event.target.value)}/><span className="workspaceCount">{visible.length} resources</span></div></div>{visible.length ? <div className="classGrid">{visible.map((item, index) => <article className="classCard" key={item.id || index}><span>{item.type || 'Resource'} · {item.status || 'available'}</span><strong>{item.title}</strong><p>{item.course || 'IMAGE programme'}</p><small>{item.resource_url ? <a href={item.resource_url} target="_blank" rel="noreferrer">Open resource ↗</a> : 'Resource link pending'}</small></article>)}</div> : <p className="emptyState">No resources match your search.</p>}</section>;
}
