INSERT INTO organizations (name, domain)
VALUES ('IMAGE Creative Education', 'image.edu.in')
ON CONFLICT (domain) DO NOTHING;

INSERT INTO branches (organization_id, code, name, state, city)
SELECT id, branch.code, branch.name, branch.state, branch.city
FROM organizations, (VALUES
  ('SLM', 'Salem', 'Tamil Nadu', 'Salem'),
  ('ADY', 'Adyar', 'Tamil Nadu', 'Chennai'),
  ('ALP', 'Alwarpet', 'Tamil Nadu', 'Chennai'),
  ('CBE', 'Coimbatore', 'Tamil Nadu', 'Coimbatore'),
  ('MDU', 'Madurai', 'Tamil Nadu', 'Madurai'),
  ('CAL', 'Calicut', 'Kerala', 'Calicut'),
  ('EKM', 'Ernakulam', 'Kerala', 'Ernakulam'),
  ('IND', 'Indira Nagar', 'Karnataka', 'Bengaluru')
) AS branch(code, name, state, city)
WHERE organizations.domain = 'image.edu.in'
ON CONFLICT (organization_id, code) DO NOTHING;

INSERT INTO courses (code, name, category, description, status)
VALUES
  ('CT-GAI', 'C-TECH with Gen AI', 'Professional Programme', 'Practice-first creative technology programme with generative AI.', 'published'),
  ('3D-VFX', '3D Animation & VFX', 'Specialization', '3D modelling, animation and visual effects.', 'published'),
  ('GUX', 'Graphic & UX / UI Design', 'Specialization', 'Brand identity, graphic design and user experience.', 'published'),
  ('GAD', 'Game Art & Design', 'Specialization', 'Game-ready art, modelling and design fundamentals.', 'published')
ON CONFLICT (code) DO NOTHING;

INSERT INTO lessons (course_id, title, sequence, content_type, status)
SELECT courses.id, lesson.title, lesson.sequence, lesson.content_type, 'published'
FROM courses, (VALUES
  ('Graphic & UX / UI Design', 'Typography fundamentals', 1, 'video'),
  ('3D Animation & VFX', 'Introduction to 3D modelling', 1, 'video')
) AS lesson(course_name, title, sequence, content_type)
WHERE courses.name = lesson.course_name
  AND NOT EXISTS (SELECT 1 FROM lessons existing WHERE existing.course_id = courses.id AND existing.title = lesson.title);

INSERT INTO assignments (lesson_id, title, description, due_at, max_score)
SELECT lessons.id, assignment.title, assignment.description, assignment.due_at::timestamptz, 100
FROM lessons, (VALUES
  ('Typography fundamentals', 'Brand identity moodboard', 'Create a visual moodboard using the typography principles.', '2026-11-09T23:59:00+05:30'),
  ('Introduction to 3D modelling', '3D character blockout', 'Submit a first-pass character blockout.', '2026-11-12T23:59:00+05:30')
) AS assignment(lesson_title, title, description, due_at)
WHERE lessons.title = assignment.lesson_title
  AND NOT EXISTS (SELECT 1 FROM assignments existing WHERE existing.lesson_id = lessons.id AND existing.title = assignment.title);

INSERT INTO exams (course_id, branch_id, title, total_marks, status)
SELECT courses.id, branches.id, exam.title, 100, exam.status
FROM courses, branches, (VALUES
  ('Graphic & UX / UI Design', 'Salem', 'Typography fundamentals quiz', 'published'),
  ('3D Animation & VFX', 'Salem', '3D modelling skills check', 'scheduled')
) AS exam(course_name, branch_name, title, status)
WHERE courses.name = exam.course_name AND branches.name = exam.branch_name
  AND NOT EXISTS (SELECT 1 FROM exams existing WHERE existing.course_id = courses.id AND existing.branch_id = branches.id AND existing.title = exam.title);
