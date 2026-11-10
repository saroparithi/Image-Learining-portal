import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function ResourceApprovalPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [items, setItems] = useState([]);
  const [message, setMessage] = useState('');
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Management') return; const token = localStorage.getItem('image-lms-token'); if (token) api.resources(token).then(result => setItems((result.items || []).filter(item => item.status !== 'published'))).catch(() => setItems([])); }, [role]);
  if (role !== 'Management') return null;
  const publish = async item => { setMessage('Publishing resource…'); try { await api.updateResource(item.id, {status: 'published'}); setItems(current => current.filter(candidate => candidate.id !== item.id)); setMessage(`${item.title} is now published.`); } catch (error) { setMessage(error.status === 403 ? 'You do not have permission to publish resources.' : 'Resource could not be published.'); } };
  return <section className="facultyActionPanel"><div><span className="eyebrow">APPROVAL QUEUE</span><strong>{items.length} resource{items.length === 1 ? '' : 's'} awaiting review</strong><p>{items[0]?.title || 'The resource queue is clear.'}</p></div>{items[0] && <button className="workspaceAction" onClick={() => publish(items[0])}>Publish latest</button>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
