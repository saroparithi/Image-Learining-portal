import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './liveSummary.css';
import RoleWorkspace from './RoleWorkspace';
import FacultyActionPanel from './FacultyActionPanel';
import ManagementActionPanel from './ManagementActionPanel';
import StudentActionPanel from './StudentActionPanel';
import AttendanceActionPanel from './AttendanceActionPanel';
import CertificateActionPanel from './CertificateActionPanel';
import FacultyAdminActionPanel from './FacultyAdminActionPanel';
import SessionActionPanel from './SessionActionPanel';
import ResourceActionPanel from './ResourceActionPanel';
import ResourceApprovalPanel from './ResourceApprovalPanel';
import BatchActionPanel from './BatchActionPanel';
import CertificateViewPanel from './CertificateViewPanel';
import LessonActionPanel from './LessonActionPanel';
import LessonCatalogPanel from './LessonCatalogPanel';
import EnrollmentActionPanel from './EnrollmentActionPanel';
import './roleWorkspace.css';
import ManagementAuditPanel from './ManagementAuditPanel';

const labels = {
  active_courses: 'Active courses', pending_assignments: 'Pending work', upcoming_sessions: 'Upcoming sessions', certificates: 'Certificates',
  assigned_classes: 'Assigned classes', pending_submissions: 'Pending submissions', attendance_to_mark: 'Attendance to mark', resources_to_publish: 'Resources to publish',
  active_students: 'Active students', active_faculty: 'Active faculty', active_batches: 'Active batches', attendance_rate: 'Attendance rate',
  active_branches: 'Active branches', active_learners: 'Active learners', published_courses: 'Published courses', network_attendance: 'Network attendance',
};

export default function LiveWorkspaceSummary({children}) {
  const [data, setData] = useState(null);
  const [quality, setQuality] = useState(null);
  const [progress, setProgress] = useState(null);
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  useEffect(() => { const sync = () => setRole(localStorage.getItem('image-lms-role') || 'Student'); const timer = window.setInterval(sync, 250); return () => window.clearInterval(timer); }, []);
  useEffect(() => { const token = localStorage.getItem('image-lms-token'); if (token) { setData(null); setQuality(null); setProgress(null); api.overview(token).then(result => { setData(result); if (result.scope === 'student') api.progress(token).then(setProgress).catch(() => setProgress(null)); if (result.scope === 'management') api.qualityReport(token).then(setQuality).catch(() => setQuality(null)); }).catch(() => setData(null)); } }, [role]);
  const summary = data?.summary || {};
  const qualitySummary = quality?.summary || {};
  const progressSummary = progress?.summary || {};
  return <>{children}<div className="workspacePanels">{data && <section className="liveWorkspaceSummary"><div><span className="eyebrow">LIVE WORKSPACE DATA</span><strong>{data.scope.replace('_', ' ')} overview</strong></div><div className="liveWorkspaceMetrics">{Object.entries(summary).map(([key, value]) => <span key={key}><b>{value}</b>{labels[key] || key.replaceAll('_', ' ')}</span>)}{Object.entries(progressSummary).filter(([key]) => ['attendance_rate','average_score','certificates','upcoming_sessions'].includes(key)).map(([key, value]) => <span className="studentMetric" key={key}><b>{value}{key.endsWith('_rate') || key === 'average_score' ? '%' : ''}</b>{labels[key] || key.replaceAll('_', ' ')}</span>)}{Object.entries(qualitySummary).map(([key, value]) => <span className="qualityMetric" key={key}><b>{value}</b>{key.replaceAll('_', ' ')}</span>)}</div></section>}<RoleWorkspace/><LessonCatalogPanel/><StudentActionPanel/><CertificateViewPanel/><FacultyActionPanel/><LessonActionPanel/><EnrollmentActionPanel/><SessionActionPanel/><ResourceActionPanel/><ResourceApprovalPanel/><BatchActionPanel/><AttendanceActionPanel/><FacultyAdminActionPanel/><CertificateActionPanel/><ManagementActionPanel/></div></>;
}
