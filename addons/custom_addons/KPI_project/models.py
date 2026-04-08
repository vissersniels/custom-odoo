from odoo import models, fields, api
from odoo.addons.project.models.project_task import CLOSED_STATES
from odoo.osv.expression import AND


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

