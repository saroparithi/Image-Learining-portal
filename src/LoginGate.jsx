import React, {useEffect, useState} from 'react';
import {ArrowRight, LockKeyhole, Sparkles} from 'lucide-react';
import {api} from './services/api';
import './login.css';
import './session.css';
import NotificationPanel from './NotificationPanel';
import ExamActionPanel from './ExamActionPanel';

export default function LoginGate({children}) {
  const [token, setToken] = useState(()=>localStorage.getItem('image-lms-token'));
  const [identifier, setIdentifier] = useState('student@image.edu.in');
  const [password, setPassword] = useState('demo');
  const [error, setError] = useState('');
  useEffect(()=>{const handleLogout=()=>setToken(null); window.addEventListener('image-lms-logout',handleLogout); return ()=>window.removeEventListener('image-lms-logout',handleLogout)},[]);
  if (token) return <><button className="sessionLogout" onClick={()=>{api.logout(); setToken(null)}}>Sign out</button><NotificationPanel/><ExamActionPanel/>{children}</>;
  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    try {
      const result = await api.login(identifier, password);
      localStorage.setItem('image-lms-token', result.access_token);
      const roleLabels = {student: 'Student', faculty: 'Faculty', branch_admin: 'Branch Admin', management: 'Management'};
      localStorage.setItem('image-lms-role', roleLabels[result.user.role] || 'Student');
      setToken(result.access_token);
    } catch (error) {
      setError(error.status === 401 ? 'Invalid email or password. Use one of the demo identities with password “demo”.' : 'The API is unavailable. Start Docker Compose, then try again.');
    }
  }
  return <main className="loginPage"><section className="loginArt"><div className="loginMark">i</div><p className="eyebrow"><Sparkles size={14}/> IMAGE CREATIVE EDUCATION</p><h1>Learning that<br/><i>moves you forward.</i></h1><p>One platform for every learner, mentor and campus across the IMAGE network.</p><span className="loginCampus">30+ campuses · 79,000+ learners</span></section><section className="loginCard"><div className="loginLogo">IMAGE <small>LMS</small></div><h2>Welcome back</h2><p>Sign in to continue to your learning workspace.</p><form onSubmit={handleSubmit}><label>Email or student ID<input value={identifier} onChange={e=>setIdentifier(e.target.value)} autoComplete="username"/></label><label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label>{error&&<div className="loginError">{error}</div>}<button type="submit">Sign in <ArrowRight size={17}/></button></form><div className="loginHint"><LockKeyhole size={15}/> Secure access for students and staff</div></section></main>;
}
