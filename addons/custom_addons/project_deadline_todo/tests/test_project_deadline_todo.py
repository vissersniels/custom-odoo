"""
Tests for project_deadline_todo.

Covers two entry points:
  1. write() override – _handle_deadline_todos() is called immediately whenever
     date_deadline changes.
  2. _cron_deadline_todos() – daily cron that scans all open tasks.

Each test method runs in its own savepoint (TransactionCase), so records
created in one test do not bleed into another.
"""

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestProjectDeadlineTodo(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Suppress all mail tracking and assignment notifications so that task
        # creation does not trigger slow QWeb email template rendering in tests.
        cls.env = cls.env(context={**cls.env.context, 'tracking_disable': True})
        cls.user = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Deadline Test User',
            'login': 'deadline_test_user',
            'groups_id': [(6, 0, [cls.env.ref('project.group_project_user').id])],
        })
        cls.project = cls.env['project.project'].with_context(mail_create_nolog=True).create({
            'name': 'Deadline Test Project',
        })

    # ── helpers ───────────────────────────────────────────────────────────────

    def _make_task(self, name='Test Task', assigned=True, extra_vals=None):
        """Create a project task. Pass assigned=False for no assignee."""
        vals = {
            'name': name,
            'project_id': self.project.id,
        }
        if assigned:
            vals['user_ids'] = [self.user.id]
        else:
            # Explicitly clear user_ids: the field default assigns self.env.user
            # if no value is provided, which would defeat the unassigned test cases.
            vals['user_ids'] = [(5, 0, 0)]
        if extra_vals:
            vals.update(extra_vals)
        return self.env['project.task'].with_context(mail_create_nolog=True).create(vals)

    def _get_todos(self, user, name=None):
        """Return private To-Dos (project_id=False) for *user*, optionally filtered by name."""
        domain = [('project_id', '=', False), ('user_ids', 'in', user.id)]
        if name:
            domain.append(('name', '=', name))
        return self.env['project.task'].search(domain)

    # ── write() / _handle_deadline_todos() tests ──────────────────────────────

    def test_write_past_deadline_creates_both_todos(self):
        """
        Setting a deadline that is already in the past immediately creates both
        a 'Deadline approaching' and a 'Deadline overdue' To-Do for the assignee,
        and sets both sent-flags on the task.
        """
        task = self._make_task('Past Deadline Task')
        past = fields.Datetime.now() - timedelta(days=2)

        task.write({'date_deadline': past})

        self.assertTrue(task.deadline_reminder_todo_sent,
                        "Reminder flag should be set for a past deadline")
        self.assertTrue(task.deadline_overdue_todo_sent,
                        "Overdue flag should be set for a past deadline")

        reminder_todos = self._get_todos(self.user, f'Deadline approaching: {task.name}')
        overdue_todos = self._get_todos(self.user, f'Deadline overdue: {task.name}')
        self.assertEqual(len(reminder_todos), 1,
                         "Exactly one reminder To-Do should be created")
        self.assertEqual(len(overdue_todos), 1,
                         "Exactly one overdue To-Do should be created")

    def test_write_deadline_within_3_days_creates_reminder_only(self):
        """
        Setting a deadline that is within the next 3 days creates only a
        'Deadline approaching' To-Do (not an overdue one).
        """
        task = self._make_task('Soon Deadline Task')
        soon = fields.Datetime.now() + timedelta(days=1)

        task.write({'date_deadline': soon})

        self.assertTrue(task.deadline_reminder_todo_sent,
                        "Reminder flag should be set for a deadline within 3 days")
        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Overdue flag must NOT be set for a future deadline")

        self.assertEqual(len(self._get_todos(self.user, f'Deadline approaching: {task.name}')), 1)
        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 0)

    def test_write_far_future_deadline_resets_flags(self):
        """
        Pushing a deadline beyond 3 days resets both sent-flags so the cron
        can fire again later. No new To-Dos are created.
        """
        task = self._make_task('Far Future Task', extra_vals={
            'deadline_reminder_todo_sent': True,
            'deadline_overdue_todo_sent': True,
        })
        far = fields.Datetime.now() + timedelta(days=10)

        task.write({'date_deadline': far})

        self.assertFalse(task.deadline_reminder_todo_sent,
                         "Reminder flag should be reset when deadline is pushed out")
        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Overdue flag should be reset when deadline is pushed out")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline approaching: {task.name}')), 0,
                         "No To-Do should be created for a far-future deadline")

    def test_write_no_duplicate_todos_when_flags_already_set(self):
        """
        Writing the same overdue deadline twice does not create a second To-Do;
        the sent-flags act as a guard.
        """
        task = self._make_task('No Duplicate Task')
        past = fields.Datetime.now() - timedelta(days=1)

        task.write({'date_deadline': past})   # first write – creates To-Dos
        task.write({'date_deadline': past})   # second write – flags already set

        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 1,
                         "Overdue To-Do must not be duplicated")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline approaching: {task.name}')), 1,
                         "Reminder To-Do must not be duplicated")

    def test_write_no_todo_without_assignee(self):
        """
        No To-Dos are created when the task has no assignee.
        Both flags must remain False.
        """
        task = self._make_task('Unassigned Task', assigned=False)
        past = fields.Datetime.now() - timedelta(days=1)

        task.write({'date_deadline': past})

        self.assertFalse(task.deadline_reminder_todo_sent)
        self.assertFalse(task.deadline_overdue_todo_sent)

    def test_write_no_todo_for_closed_task(self):
        """
        No To-Dos are created when the task is already in a closed state
        ('1_done' or '1_canceled').
        """
        task = self._make_task('Closed Task')
        task.write({'state': '1_done'})
        past = fields.Datetime.now() - timedelta(days=1)

        task.write({'date_deadline': past})

        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Closed tasks must not trigger To-Do creation")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 0)

    def test_write_no_todo_for_private_task_without_project(self):
        """
        No To-Dos are created for private tasks (project_id=False), since the
        module only targets project tasks.
        """
        private_task = self.env['project.task'].create({
            'name': 'Private Task',
            'project_id': False,
            'user_ids': [self.user.id],
        })
        initial_count = len(self._get_todos(self.user))
        past = fields.Datetime.now() - timedelta(days=1)

        private_task.write({'date_deadline': past})

        self.assertEqual(len(self._get_todos(self.user)), initial_count,
                         "write() on a private task must not create any To-Dos")

    def test_write_multiple_assignees_each_get_todos(self):
        """
        Every assignee of a task receives their own reminder and overdue To-Dos.
        """
        user2 = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Deadline Test User 2',
            'login': 'deadline_test_user2',
            'groups_id': [(6, 0, [self.env.ref('project.group_project_user').id])],
        })
        task = self._make_task('Multi User Task', extra_vals={'user_ids': [self.user.id, user2.id]})
        past = fields.Datetime.now() - timedelta(days=1)

        task.write({'date_deadline': past})

        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 1,
                         "User 1 must receive an overdue To-Do")
        self.assertEqual(len(self._get_todos(user2, f'Deadline overdue: {task.name}')), 1,
                         "User 2 must receive an overdue To-Do")

    def test_write_todo_content_references_task_and_project(self):
        """
        The description of a created To-Do must mention both the task name and
        the project name.
        """
        task = self._make_task('Content Check Task')
        past = fields.Datetime.now() - timedelta(days=5)
        task.write({'date_deadline': past})

        overdue_todo = self._get_todos(self.user, f'Deadline overdue: {task.name}')
        self.assertEqual(len(overdue_todo), 1)
        self.assertIn(task.name, overdue_todo.description,
                      "To-Do description must mention the task name")
        self.assertIn(self.project.name, overdue_todo.description,
                      "To-Do description must mention the project name")

    # ── cron / _cron_deadline_todos() tests ───────────────────────────────────

    def test_cron_creates_reminder_todo_for_approaching_deadline(self):
        """
        The daily cron creates a reminder To-Do for an open task whose deadline
        falls within the next 3 days and whose reminder flag is not yet set.

        Note: the task is created with date_deadline in the create() dict so
        that write() is not called and the flag stays False until the cron runs.
        """
        task = self._make_task('Cron Reminder Task', extra_vals={
            'date_deadline': fields.Datetime.now() + timedelta(days=2),
        })
        self.assertFalse(task.deadline_reminder_todo_sent,
                         "Flag must be False before the cron runs")

        self.env['project.task']._cron_deadline_todos()

        self.assertTrue(task.deadline_reminder_todo_sent,
                        "Cron must set the reminder flag after running")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline approaching: {task.name}')), 1,
                         "Cron must have created exactly one reminder To-Do")

    def test_cron_creates_overdue_todo_for_past_deadline(self):
        """
        The daily cron creates an overdue To-Do for a task whose deadline has
        already passed and whose overdue flag is not yet set.
        """
        task = self._make_task('Cron Overdue Task', extra_vals={
            'date_deadline': fields.Datetime.now() - timedelta(days=1),
        })
        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Flag must be False before the cron runs")

        self.env['project.task']._cron_deadline_todos()

        self.assertTrue(task.deadline_overdue_todo_sent,
                        "Cron must set the overdue flag after running")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 1,
                         "Cron must have created exactly one overdue To-Do")

    def test_cron_does_not_duplicate_todos_when_flag_already_set(self):
        """
        The cron must not create a To-Do if the flag is already True, even if
        the deadline is still in the overdue range.
        """
        task = self._make_task('Cron No Dup Task', extra_vals={
            'date_deadline': fields.Datetime.now() - timedelta(days=1),
            'deadline_overdue_todo_sent': True,
        })

        self.env['project.task']._cron_deadline_todos()

        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 0,
                         "Cron must not create a duplicate overdue To-Do")

    def test_cron_skips_closed_tasks(self):
        """
        The cron must not create overdue To-Dos for tasks that are in a closed
        state, even if the deadline has passed.
        """
        task = self._make_task('Cron Closed Task', extra_vals={
            'date_deadline': fields.Datetime.now() - timedelta(days=1),
        })
        task.write({'state': '1_done'})

        self.env['project.task']._cron_deadline_todos()

        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Cron must not set the overdue flag for a closed task")
        self.assertEqual(len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 0)

    def test_cron_skips_tasks_without_assignee(self):
        """
        The cron must not create any To-Do for tasks that have no assigned user.
        """
        task = self._make_task('Cron No User Task', assigned=False, extra_vals={
            'date_deadline': fields.Datetime.now() - timedelta(days=1),
        })

        self.env['project.task']._cron_deadline_todos()

        # The cron may legitimately create To-Dos for other pre-existing tasks in
        # the DB. Only assert that NO To-Do was created for *this* unassigned task.
        self.assertFalse(task.deadline_overdue_todo_sent,
                         "Cron must not set the overdue flag for an unassigned task")
        self.assertFalse(task.deadline_reminder_todo_sent,
                         "Cron must not set the reminder flag for an unassigned task")
        self.assertEqual(
            len(self._get_todos(self.user, f'Deadline overdue: {task.name}')), 0,
            "Cron must not create an overdue To-Do for an unassigned task",
        )

    def test_cron_skips_private_tasks_without_project(self):
        """
        The cron must not create To-Dos for private tasks (project_id=False).
        """
        private_task = self.env['project.task'].create({
            'name': 'Cron Private Task',
            'project_id': False,
            'user_ids': [self.user.id],
            'date_deadline': fields.Datetime.now() - timedelta(days=1),
        })
        initial_count = len(self._get_todos(self.user))

        self.env['project.task']._cron_deadline_todos()

        self.assertEqual(len(self._get_todos(self.user)), initial_count,
                         "Cron must not create any To-Do for a private task")
        self.assertFalse(private_task.deadline_overdue_todo_sent)
