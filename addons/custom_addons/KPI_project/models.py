from datetime import timedelta

from odoo import models, fields, api
from odoo.addons.project.models.project_task import CLOSED_STATES
from odoo.osv.expression import AND


class ProjectKPISnapshot(models.Model):
    _name = 'project.kpi.snapshot'
    _description = 'Project Manager Workload Snapshot'
    _order = 'snapshot_date desc, user_id'

    snapshot_date = fields.Date(string='Snapshot Date', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Project Manager', required=True, index=True)
    workload = fields.Integer(string='Active Projects')

    @api.model
    def _take_snapshot(self):
        """
        Called weekly by ir.cron.
        Records, for each manager with at least one active project, how many
        active projects they are currently responsible for.
        """
        today = fields.Date.context_today(self)
        result = self.env['project.project']._read_group(
            [('active', '=', True), ('user_id', '!=', False)],
            ['user_id'],
            ['__count'],
        )
        rows = [
            {'snapshot_date': today, 'user_id': user.id, 'workload': count}
            for user, count in result
        ]
        if rows:
            self.create(rows)


class ProjectKPI(models.Model):
    _inherit = 'project.project'

    # KPI Fields
    total_tasks = fields.Integer(compute='_compute_task_stats', string='Total Tasks')
    completed_tasks = fields.Integer(compute='_compute_task_stats', string='Completed Tasks')
    active_tasks = fields.Integer(compute='_compute_task_stats', string='Active Tasks')
    completion_rate = fields.Float(compute='_compute_task_stats', string='Completion Rate (%)')
    manager_workload = fields.Integer(compute='_compute_manager_workload', string='Manager Load')

    def _compute_task_stats(self):
        """
        Compute task KPIs using _read_group directly on project.task.
        task_ids has domain=[('is_closed', '=', False)] so it never contains
        closed tasks — we must bypass it and query the model directly.
        No @api.depends mirrors Odoo's own task_count / closed_task_count pattern:
        the field always recomputes fresh on access.
        """
        Task = self.env['project.task']
        base_domain = [('project_id', 'in', self.ids), ('display_in_project', '=', True)]

        total_by_project = dict(Task._read_group(base_domain, ['project_id'], ['__count']))
        closed_by_project = dict(Task._read_group(
            AND([base_domain, [('state', 'in', list(CLOSED_STATES))]]),
            ['project_id'], ['__count'],
        ))

        for project in self:
            total = total_by_project.get(project, 0)
            completed = closed_by_project.get(project, 0)
            project.total_tasks = total
            project.completed_tasks = completed
            project.active_tasks = total - completed
            # percentage widget multiplies by 100 for display, so store as 0.0–1.0 fraction
            project.completion_rate = (completed / total) if total > 0 else 0.0

    def _compute_manager_workload(self):
        """
        Count the number of active projects assigned to each project's manager.
        This gives a 'load' indicator: how many projects that manager is responsible for.
        """
        manager_ids = self.mapped('user_id').ids
        if not manager_ids:
            self.manager_workload = 0
            return
        result = self.env['project.project']._read_group(
            [('user_id', 'in', manager_ids), ('active', '=', True)],
            ['user_id'], ['__count'],
        )
        workload_by_manager = {user.id: count for user, count in result}
        for project in self:
            project.manager_workload = workload_by_manager.get(project.user_id.id, 0)


class ProjectTasksCompletedSnapshot(models.Model):
    _name = 'project.kpi.tasks.completed.snapshot'
    _description = 'Tasks Completed Per Week Snapshot'
    _order = 'snapshot_date desc, user_id'

    snapshot_date = fields.Date(string='Week Start', required=True, index=True)
    user_id = fields.Many2one('res.users', string='Assignee', required=True, index=True)
    tasks_completed = fields.Integer(string='Tasks Completed')

    @api.model
    def _take_snapshot(self):
        """
        Called weekly by ir.cron.
        Records, for each assignee, how many tasks they completed (transitioned to
        a closed state) during the past seven days.
        """
        today = fields.Date.context_today(self)
        week_start = today - timedelta(days=7)

        result = self.env['project.task']._read_group(
            [
                ('state', 'in', list(CLOSED_STATES)),
                ('date_last_stage_update', '>=', week_start),
                ('date_last_stage_update', '<', today),
                ('display_in_project', '=', True),
                ('user_ids', '!=', False),
            ],
            ['user_ids'],
            ['__count'],
        )
        rows = [
            {'snapshot_date': week_start, 'user_id': user.id, 'tasks_completed': count}
            for user, count in result
            if user.id
        ]
        if rows:
            self.create(rows)


class ProjectKPIPlanningSnapshot(models.Model):
    _name = 'project.kpi.planning.snapshot'
    _description = 'Task Planning Completeness Snapshot'
    _order = 'snapshot_date desc'

    snapshot_date = fields.Date(string='Snapshot Date', required=True, index=True)
    total_projects = fields.Integer(string='Total Active Projects')
    planned_projects = fields.Integer(string='Projects with Planned Tasks')
    # Stored as 0.0–100.0 so graph Y-axis reads as a percentage directly
    completeness_rate = fields.Float(string='Completeness Rate (%)', digits=(5, 2))

    @api.model
    def _take_snapshot(self):
        """
        Called daily by ir.cron.
        A project counts as "planned" when it has at least one task with:
          - at least one assignee (user_ids)
          - a deadline (date_deadline)
          - a state explicitly set (state is always populated in Odoo,
            so this is satisfied by any task that meets the above two conditions)
        The snapshot stores the total active project count, how many of those
        are "planned", and the resulting completeness percentage.
        """
        today = fields.Date.context_today(self)

        total_result = self.env['project.project']._read_group(
            [('active', '=', True)],
            [],
            ['__count'],
        )
        total = total_result[0][0] if total_result else 0

        if total == 0:
            self.create({
                'snapshot_date': today,
                'total_projects': 0,
                'planned_projects': 0,
                'completeness_rate': 0.0,
            })
            return

        # One row per distinct project that has at least 1 qualifying task
        planned_result = self.env['project.task']._read_group(
            [
                ('display_in_project', '=', True),
                ('project_id.active', '=', True),
                ('user_ids', '!=', False),
                ('date_deadline', '!=', False),
                ('state', '!=', False),
            ],
            ['project_id'],
            ['__count'],
        )
        planned = len(planned_result)

        self.create({
            'snapshot_date': today,
            'total_projects': total,
            'planned_projects': planned,
            'completeness_rate': (planned / total) * 100.0,
        })


class ProjectKPIStalenessSnapshot(models.Model):
    _name = 'project.kpi.staleness.snapshot'
    _description = 'Project Staleness Snapshot'
    _order = 'snapshot_date desc, project_id'

    snapshot_date = fields.Date(string='Snapshot Date', required=True, index=True)
    project_id = fields.Many2one(
        'project.project', string='Project',
        required=True, index=True, ondelete='cascade',
    )
    days_since_last_update = fields.Float(string='Days Since Last Update', digits=(10, 1))

    @api.model
    def _take_snapshot(self):
        """
        Called daily by ir.cron.
        For each active project, computes how many days have passed since it was
        last touched.  'Last touched' is the most recent of:
          - the project's own write_date (field edits on the project record)
          - the max write_date of its tasks (task field edits)
          - the max date of messages posted directly on the project chatter
            (notes, emails, log entries)
        """
        today_date = fields.Date.context_today(self)
        now = fields.Datetime.now()

        projects = self.env['project.project'].search([('active', '=', True)])
        if not projects:
            return

        project_ids = projects.ids

        # Latest task write_date per project
        task_result = self.env['project.task']._read_group(
            [('project_id', 'in', project_ids), ('display_in_project', '=', True)],
            ['project_id'],
            ['write_date:max'],
        )
        task_last = {project.id: max_dt for project, max_dt in task_result if max_dt}

        # Latest chatter message date per project (notes, emails, internal logs)
        msg_result = self.env['mail.message'].sudo()._read_group(
            [('res_model', '=', 'project.project'), ('res_id', 'in', project_ids)],
            ['res_id'],
            ['date:max'],
        )
        msg_last = {res_id: max_date for res_id, max_date in msg_result if max_date}

        rows = []
        for project in projects:
            candidates = [dt for dt in [
                project.write_date,
                task_last.get(project.id),
                msg_last.get(project.id),
            ] if dt]
            if not candidates:
                continue
            last_update = max(candidates)
            delta = now - last_update
            days = delta.total_seconds() / 86400.0
            rows.append({
                'snapshot_date': today_date,
                'project_id': project.id,
                'days_since_last_update': max(0.0, days),
            })

        if rows:
            self.create(rows)

