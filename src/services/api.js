const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const token = localStorage.getItem('image-lms-token');
  const response = await fetch(API_BASE + path, {
    ...options,
    headers: {'Content-Type': 'application/json', ...(token ? {Authorization: 'Bearer ' + token} : {}), ...(options.headers || {})},
  });
  // Only clear the session when the identity check itself rejects the token.
  // Role-restricted endpoints also use 401 for a valid user without access;
  // logging out on those responses makes successful logins appear to fail.
  if (response.status === 401 && path === '/api/v1/auth/me') {
    localStorage.removeItem('image-lms-token');
    localStorage.removeItem('image-lms-role');
    window.dispatchEvent(new Event('image-lms-logout'));
  }
  if (!response.ok) { const error = new Error('API request failed: ' + response.status); error.status = response.status; throw error; }
  const result = await response.json();
  if (options.method && options.method !== 'GET') window.dispatchEvent(new Event('image-lms-data-changed'));
  return result;
}

export const api = {
  health: () => request('/health'),
  workspaces: () => request('/api/v1/workspaces'),
  branches: () => request('/api/v1/branches'),
  login: (identifier, password) => request('/api/v1/auth/login', {method: 'POST', body: JSON.stringify({identifier, password})}),
  me: token => request('/api/v1/auth/me', {headers: {Authorization: 'Bearer ' + token}}),
  students: token => request('/api/v1/students', {headers: {Authorization: 'Bearer ' + token}}),
  batches: token => request('/api/v1/batches', {headers: {Authorization: 'Bearer ' + token}}),
  enrollments: token => request('/api/v1/enrollments', {headers: {Authorization: 'Bearer ' + token}}),
  faculty: token => request('/api/v1/faculty', {headers: {Authorization: 'Bearer ' + token}}),
  facultyClasses: token => request('/api/v1/faculty/classes', {headers: {Authorization: 'Bearer ' + token}}),
  audit: token => request('/api/v1/audit', {headers: {Authorization: 'Bearer ' + token}}),
  courses: token => request('/api/v1/courses', {headers: {Authorization: 'Bearer ' + token}}),
  assignments: token => request('/api/v1/assignments', {headers: {Authorization: 'Bearer ' + token}}),
  createAssignment: data => request('/api/v1/assignments', {method: 'POST', body: JSON.stringify(data)}),
  submissions: token => request('/api/v1/assignments/submissions', {headers: {Authorization: 'Bearer ' + token}}),
  attendance: token => request('/api/v1/attendance', {headers: {Authorization: 'Bearer ' + token}}),
  lessons: token => request('/api/v1/lessons', {headers: {Authorization: 'Bearer ' + token}}),
  resources: token => request('/api/v1/resources', {headers: {Authorization: 'Bearer ' + token}}),
  exams: token => request('/api/v1/exams', {headers: {Authorization: 'Bearer ' + token}}),
  createExam: data => request('/api/v1/exams', {method: 'POST', body: JSON.stringify(data)}),
  updateExam: (id, data) => request('/api/v1/exams/' + id, {method: 'PATCH', body: JSON.stringify(data)}),
  attempts: token => request('/api/v1/exams/attempts', {headers: {Authorization: 'Bearer ' + token}}),
  certificates: token => request('/api/v1/certificates', {headers: {Authorization: 'Bearer ' + token}}),
  notifications: token => request('/api/v1/notifications', {headers: {Authorization: 'Bearer ' + token}}),
  updateNotification: (id, data) => request('/api/v1/notifications/' + id, {method: 'PATCH', body: JSON.stringify(data)}),
  sessions: token => request('/api/v1/sessions', {headers: {Authorization: 'Bearer ' + token}}),
  createSession: data => request('/api/v1/sessions', {method: 'POST', body: JSON.stringify(data)}),
  overview: token => request('/api/v1/reports/overview', {headers: {Authorization: 'Bearer ' + token}}),
  dashboard: token => request('/api/v1/reports/dashboard', {headers: {Authorization: 'Bearer ' + token}}),
  branchReport: token => request('/api/v1/reports/branches', {headers: {Authorization: 'Bearer ' + token}}),
  attendanceReport: token => request('/api/v1/reports/attendance', {headers: {Authorization: 'Bearer ' + token}}),
  progress: token => request('/api/v1/reports/progress', {headers: {Authorization: 'Bearer ' + token}}),
  qualityReport: token => request('/api/v1/reports/quality', {headers: {Authorization: 'Bearer ' + token}}),
  createBranch: data => request('/api/v1/branches', {method: 'POST', body: JSON.stringify(data)}),
  createCourse: data => request('/api/v1/courses', {method: 'POST', body: JSON.stringify(data)}),
  updateCourse: (code, data) => request('/api/v1/courses/' + code, {method: 'PATCH', body: JSON.stringify(data)}),
  createBatch: data => request('/api/v1/batches', {method: 'POST', body: JSON.stringify(data)}),
  createEnrollment: data => request('/api/v1/enrollments', {method: 'POST', body: JSON.stringify(data)}),
  createStudent: data => request('/api/v1/students', {method: 'POST', body: JSON.stringify(data)}),
  createFaculty: data => request('/api/v1/faculty', {method: 'POST', body: JSON.stringify(data)}),
  createLesson: data => request('/api/v1/lessons', {method: 'POST', body: JSON.stringify(data)}),
  updateLesson: (id, data) => request('/api/v1/lessons/' + id, {method: 'PATCH', body: JSON.stringify(data)}),
  createResource: data => request('/api/v1/resources', {method: 'POST', body: JSON.stringify(data)}),
  updateResource: (id, data) => request('/api/v1/resources/' + id, {method: 'PATCH', body: JSON.stringify(data)}),
  recordAttendance: data => request('/api/v1/attendance', {method: 'POST', body: JSON.stringify(data)}),
  recordBulkAttendance: data => request('/api/v1/attendance/bulk', {method: 'POST', body: JSON.stringify(data)}),
  submitAssignment: data => request('/api/v1/assignments/submissions', {method: 'POST', body: JSON.stringify(data)}),
  gradeSubmission: (id, data) => request('/api/v1/assignments/submissions/' + id, {method: 'PATCH', body: JSON.stringify(data)}),
  submitExamAttempt: data => request('/api/v1/exams/attempts', {method: 'POST', body: JSON.stringify(data)}),
  issueCertificate: data => request('/api/v1/certificates', {method: 'POST', body: JSON.stringify(data)}),
  logout: () => {
    localStorage.removeItem('image-lms-token');
    localStorage.removeItem('image-lms-role');
  },
};
