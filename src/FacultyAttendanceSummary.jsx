import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultyAttendanceSummary() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [items, setItems] = useState([]);
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'Attendance') return; const token = localStorage.getItem('image-lms-token'); if (token) api.attendance(token).then(result => setItems(result.items || [])).catch(() => setItems([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'Attendance') return null;
  const present = items.filter(item => item.status === 'present').length; const late = items.filter(item => item.status === 'late').length; const absent = items.filter(item => item.status === 'absent').length; const rate = items.length ? Math.round((present + late) / items.length * 1000) / 10 : 0;
  return <section className="roleWorkspace facultyClasses"><div className="roleWorkspaceHead"><div><span className="eyebrow">FACULTY PORTAL</span><h2>Attendance report</h2><p>Review attendance activity recorded for your students.</p></div><span className="workspaceCount">{items.length} records</span></div><div className="attendanceMetrics"><div><b>{rate}%</b><span>Attendance rate</span></div><div><b>{present}</b><span>Present</span></div><div><b>{late}</b><span>Late</span></div><div><b>{absent}</b><span>Absent</span></div></div>{!items.length && <p className="emptyState">No attendance records are available yet.</p>}</section>;
}
