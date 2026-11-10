import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function CertificateViewPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [certificates, setCertificates] = useState([]);
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Student') return; const token = localStorage.getItem('image-lms-token'); if (token) api.certificates(token).then(result => setCertificates(result.items || [])).catch(() => setCertificates([])); }, [role]);
  if (role !== 'Student') return null;
  return <section className="facultyActionPanel"><div><span className="eyebrow">CREDENTIALS</span><strong>{certificates.length} certificate{certificates.length === 1 ? '' : 's'} earned</strong><p>{certificates[0]?.course || 'Complete a course to earn your first credential.'}</p>{certificates.length > 1 && <small>{certificates.slice(0, 3).map(item => item.certificate_number || item.course).join(' · ')}</small>}</div>{certificates[0]?.certificate_url && <a className="workspaceAction" href={certificates[0].certificate_url} target="_blank" rel="noreferrer">View latest certificate</a>}</section>;
}
