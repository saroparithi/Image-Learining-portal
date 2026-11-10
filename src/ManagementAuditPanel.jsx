import React, {useEffect, useMemo, useState} from 'react';
import {api} from './services/api';
import './managementAudit.css';

export default function ManagementAuditPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview');
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Management' || section !== 'Audit logs') return; const token = localStorage.getItem('image-lms-token'); if (token) api.audit(token).then(result => setItems(result.items || [])).catch(() => setItems([])); }, [role, section]);
  const filtered = useMemo(() => items.filter(item => JSON.stringify(item).toLowerCase().includes(query.trim().toLowerCase())), [items, query]);
  function exportCsv() { const rows = [['Date', 'Action', 'Entity', 'Actor'], ...filtered.map(item => [item.created_at || '', item.action || '', item.entity_type || '', item.actor_name || item.actor_id || ''])]; const csv = rows.map(row => row.map(value => JSON.stringify(String(value))).join(',')).join('\n'); const url = URL.createObjectURL(new Blob([csv], {type:'text/csv'})); const link = document.createElement('a'); link.href = url; link.download = 'image-audit-log.csv'; link.click(); URL.revokeObjectURL(url); }
  if (role !== 'Management' || section !== 'Audit logs') return null;
  return <section className="facultyActionPanel managementAuditPanel"><div className="auditHead"><div><span className="eyebrow">GOVERNANCE</span><strong>Audit log</strong><p>Review organization activity and changes.</p></div><div className="workspaceActions"><input aria-label="Filter audit log" placeholder="Filter activity..." value={query} onChange={event => setQuery(event.target.value)} /><button className="workspaceAction" onClick={exportCsv} disabled={!filtered.length}>Export CSV</button></div></div><div className="auditRows">{filtered.map((item, index) => <div className="auditRow" key={item.id || index}><b>{item.action || 'Activity'}</b><span>{item.entity_type || 'Record'}</span><small>{item.actor_name || item.actor_id || 'System'} · {item.created_at ? new Date(item.created_at).toLocaleString() : 'Recently'}</small></div>)}{!filtered.length && <p className="emptyState">No audit activity matches this filter.</p>}</div></section>;
}
