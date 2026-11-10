import React, {useEffect, useState} from 'react';
import {api} from './services/api';

export default function LessonActionPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student');
  const [section, setSection] = useState(() => document.body.dataset.lmsSection || 'Overview');
  const [lessons, setLessons] = useState([]);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [form, setForm] = useState({course: 'Graphic & UX / UI Design', module: 'Design foundations', title: '', sequence: 1, content_type: 'lesson'});

  useEffect(() => {
    const sync = () => { setRole(localStorage.getItem('image-lms-role') || 'Student'); setSection(document.body.dataset.lmsSection || 'Overview'); };
    const timer = window.setInterval(sync, 250);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (role !== 'Management' || section !== 'Courses') return;
    const token = localStorage.getItem('image-lms-token');
    if (token) api.lessons(token).then(result => setLessons((result.items || []).filter(item => !item.published))).catch(() => setLessons([]));
  }, [role, section]);

  if ((role === 'Faculty' && ['My classes', 'Resources'].includes(section)) || (role === 'Branch Admin' && section === 'Courses')) {
    const submit = async event => {
      event.preventDefault(); setMessage('Saving lesson draft…');
      try {
        await api.createLesson({...form, sequence: Number(form.sequence)});
        setForm({...form, title: '', sequence: Number(form.sequence) + 1});
        setOpen(false); setMessage('Lesson draft created and sent for approval.');
        window.dispatchEvent(new Event('image-lms-data-changed'));
      } catch (error) { setMessage(error.status === 404 ? 'Course was not found.' : 'Lesson could not be created.'); }
    };
    return <section className="facultyActionPanel"><div><span className="eyebrow">LESSON AUTHORING</span><strong>Create a lesson draft</strong><p>{role === 'Branch Admin' ? 'Prepare branch learning content for management approval.' : 'Prepare structured learning content for management approval.'}</p></div><button className="workspaceAction" onClick={() => setOpen(value => !value)}>+ Add lesson</button>{open && <form className="workspaceForm" onSubmit={submit}><input required placeholder="Course" value={form.course} onChange={e => setForm({...form, course: e.target.value})}/><input required placeholder="Module" value={form.module} onChange={e => setForm({...form, module: e.target.value})}/><input required placeholder="Lesson title" value={form.title} onChange={e => setForm({...form, title: e.target.value})}/><input required type="number" min="1" placeholder="Sequence" value={form.sequence} onChange={e => setForm({...form, sequence: e.target.value})}/><select value={form.content_type} onChange={e => setForm({...form, content_type: e.target.value})}><option value="lesson">Lesson</option><option value="video">Video</option><option value="workshop">Workshop</option></select><button type="submit">Save draft</button></form>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
  }

  if (role !== 'Management' || section !== 'Courses') return null;
  const publish = async lesson => {
    setMessage('Publishing lesson…');
    try { await api.updateLesson(lesson.id, {published: true}); setLessons(items => items.filter(item => item.id !== lesson.id)); setMessage(`${lesson.title} is now visible to students.`); }
    catch { setMessage('Lesson could not be published.'); }
  };
  return <section className="facultyActionPanel"><div><span className="eyebrow">LESSON APPROVAL</span><strong>{lessons.length} lesson{lessons.length === 1 ? '' : 's'} awaiting approval</strong><p>{lessons[0]?.title || 'The lesson queue is clear.'}</p></div>{lessons[0] && <button className="workspaceAction" onClick={() => publish(lessons[0])}>Publish latest</button>}{message && <span className="facultyActionMessage">{message}</span>}</section>;
}
