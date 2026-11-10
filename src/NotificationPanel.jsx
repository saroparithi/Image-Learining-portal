import React, {useEffect, useState} from 'react';
import {api} from './services/api';
import './notification.css';
export default function NotificationPanel() {
  const [role, setRole] = useState(() => localStorage.getItem('image-lms-role') || 'Student'); const [items, setItems] = useState([]); const [open, setOpen] = useState(false);
  useEffect(() => { const timer = window.setInterval(() => setRole(localStorage.getItem('image-lms-role') || 'Student'), 250); return () => window.clearInterval(timer); }, []);
  useEffect(() => { const load = () => { if (localStorage.getItem('image-lms-token')) api.notifications().then(result => setItems(result.items || [])).catch(() => setItems([])); }; load(); window.addEventListener('image-lms-data-changed', load); return () => window.removeEventListener('image-lms-data-changed', load); }, [role]);
  const unread = items.filter(item => !item.read).length;
  async function markRead(item) { await api.updateNotification(item.id, {read:true}).catch(() => null); setItems(items.map(value => value.id === item.id ? {...value, read:true} : value)); }
  if (!items.length) return null;
  return <section className="notificationPanel"><button className="notificationToggle" onClick={() => setOpen(value => !value)}><span className="eyebrow">NOTIFICATIONS</span><strong>{unread ? `${unread} unread notification${unread === 1 ? '' : 's'}` : 'All notifications read'}</strong></button>{open && <div className="notificationList">{items.slice(0,5).map(item => <button className={item.read ? 'notificationRead' : ''} key={item.id} onClick={() => markRead(item)}><b>{item.title}</b><span>{item.message}</span></button>)}</div>}</section>;
}
