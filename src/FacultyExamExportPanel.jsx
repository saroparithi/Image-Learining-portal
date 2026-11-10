import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './facultyPortal.css';

export default function FacultyExamExportPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview'); const [attempts, setAttempts] = useState([]);
  useEffect(() => { const timer = setInterval(() => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); }, 250); return () => clearInterval(timer); }, []);
  useEffect(() => { if (role !== 'Faculty' || section !== 'Exams') return; const token = localStorage.getItem('image-lms-token'); if (token) api.attempts(token).then(result => setAttempts(result.items || [])).catch(() => setAttempts([])); }, [role, section]);
  if (role !== 'Faculty' || section !== 'Exams') return null;
  function exportResults() { const rows = [['Exam', 'Student', 'Score', 'Max score'], ...attempts.map(item => [item.exam_id || '', item.student_name || item.student_id || '', item.score ?? '', item.max_score || 100])]; const csv = rows.map(row => row.map(value => JSON.stringify(String(value))).join(',')).join('\n'); const url = URL.createObjectURL(new Blob([csv], {type:'text/csv'})); const link = document.createElement('a'); link.href = url; link.download = 'image-exam-results.csv'; link.click(); URL.revokeObjectURL(url); }
  return <section className="facultyActionPanel"><div><span className="eyebrow">EXAM REPORTING</span><strong>Exam results export</strong><p>{attempts.length} student attempts available.</p></div><button className="workspaceAction" onClick={exportResults} disabled={!attempts.length}>Download results CSV</button></section>;
}
