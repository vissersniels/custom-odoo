from datetime import timedelta

from odoo import api, fields, models
from odoo.addons.project.models.project_task import CLOSED_STATES


class ProjectTask(models.Model):
    _inherit = 'project.task'

    deadline_reminder_todo_sent = fields.Boolean(
        string='3-Day Reminder To-Do Sent',
        default=False,
        copy=False,
    )
    deadline_overdue_todo_sent = fields.Boolean(
        string='Overdue To-Do Sent',
        default=False,
        copy=False,
    )

    def write(self, vals):
        res = super().write(vals)
        if 'date_deadline' in vals:
            self._handle_deadline_todos()
        return res

    def _handle_deadline_todos(self):
        """
        Called after a write that changed date_deadline.
        Immediately creates To-Dos when the new deadline is within 3 days or
        already past, and resets the sent-flags when the deadline is pushed out.
        """
        now = fields.Datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        in_3_days_end = today_start + timedelta(days=3, hours=23, minutes=59, seconds=59)

        for task in self:
            if not task.project_id or task.state in CLOSED_STATES or not task.user_ids:
                continue
            deadline = task.date_deadline
            if not deadline:
                continue

            if deadline < today_start:
                # Deadline is already in the past
                if not task.deadline_reminder_todo_sent:
                    task._create_deadline_todo('reminder')
                    task.deadline_reminder_todo_sent = True
                if not task.deadline_overdue_todo_sent:
                    task._create_deadline_todo('overdue')
                    task.deadline_overdue_todo_sent = True

            elif deadline <= in_3_days_end:
                # Deadline is in the future but within 3 days
                if not task.deadline_reminder_todo_sent:
                    task._create_deadline_todo('reminder')
                    task.deadline_reminder_todo_sent = True

            else:
                # Deadline pushed beyond 3 days - reset so cron can fire again
                task.deadline_reminder_todo_sent = False
                task.deadline_overdue_todo_sent = False

    def _create_deadline_todo(self, kind):
        """Creates a private To-Do for each assignee of the task."""
        self.ensure_one()
        deadline_str = self.date_deadline.strftime('%d/%m/%Y') if self.date_deadline else ''
        if kind == 'reminder':
            name = f"Deadline approaching: {self.name}"
            description = (
                f"<p>The task <b>{self.name}</b> in project <b>{self.project_id.name}</b> "
                f"is due on {deadline_str}. Please make sure to complete it on time.</p>"
            )
        else:
            name = f"Deadline overdue: {self.name}"
            description = (
                f"<p>The task <b>{self.name}</b> in project <b>{self.project_id.name}</b> "
                f"was due on {deadline_str} and is now overdue.</p>"
            )
        for user in self.user_ids:
            self.env['project.task'].create({
                'name': name,
                'user_ids': [user.id],
                'project_id': False,
                'date_deadline': self.date_deadline,
                'description': description,
            })

    @api.model
    def _cron_deadline_todos(self):
        """
        Daily cron job.
        1. Creates 3-day reminder To-Dos for open tasks whose deadline falls
           within the next 3 days and whose reminder has not yet been sent.
        2. Creates overdue To-Dos for open tasks whose deadline has already
           passed and whose overdue notice has not yet been sent.
        """
        now = fields.Datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        in_3_days_end = today_start + timedelta(days=3, hours=23, minutes=59, seconds=59)

        reminder_tasks = self.search([
            ('project_id', '!=', False),
            ('date_deadline', '>=', today_start),
            ('date_deadline', '<=', in_3_days_end),
            ('deadline_reminder_todo_sent', '=', False),
            ('state', 'not in', list(CLOSED_STATES)),
            ('user_ids', '!=', False),
        ])
        for task in reminder_tasks:
            task._create_deadline_todo('reminder')
            task.deadline_reminder_todo_sent = True

        overdue_tasks = self.search([
            ('project_id', '!=', False),
            ('date_deadline', '<', today_start),
            ('deadline_overdue_todo_sent', '=', False),
            ('state', 'not in', list(CLOSED_STATES)),
            ('user_ids', '!=', False),
        ])
        for task in overdue_tasks:
            task._create_deadline_todo('overdue')
            task.deadline_overdue_todo_sent = True
