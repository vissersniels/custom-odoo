from odoo import fields, models


class OutstandingOrderComparison(models.Model):
    _name = 'outstanding.order.comparison'
    _description = 'Outstanding Order Comparison'

    name = fields.Char(string='Name', default='Outstanding Order Comparison')

    file_one = fields.Binary(string='Odoo Outstanding List', attachment=True)
    file_one_name = fields.Char(string='Odoo Outstanding List Name')

    file_two = fields.Binary(string='Higo Outstanding List', attachment=True)
    file_two_name = fields.Char(string='Higo Outstanding List Name')
    higo_outstanding_date = fields.Date(string='Higo Outstanding List Date')

    output_file = fields.Binary(string='Output File', attachment=True, readonly=True)
    output_file_name = fields.Char(string='Output File Name', readonly=True)

    def action_set_higo_outstanding_date(self):
        self.ensure_one()
        self.higo_outstanding_date = fields.Date.context_today(self)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_run_program(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Run complete',
                'message': 'Placeholder program executed.',
                'type': 'success',
                'sticky': False,
            },
        }

    def action_process_files(self):
        """Override this method with your custom Python logic.

        Both uploaded files are available as base64-encoded bytes via
        self.file_one and self.file_two.  Write the result back to
        self.output_file / self.output_file_name to make it downloadable.
        """
        import base64

        # Decode the uploaded files
        # file_one_bytes = base64.b64decode(self.file_one)
        # file_two_bytes = base64.b64decode(self.file_two)

        # TODO: run your comparison logic here and build result_bytes
        # result_bytes = ...

        # Write the output so the user can download it
        # self.write({
        #     'output_file': base64.b64encode(result_bytes),
        #     'output_file_name': 'comparison_result.xlsx',
        # })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Not implemented yet',
                'message': 'Add your processing logic inside action_process_files().',
                'type': 'warning',
                'sticky': False,
            },
        }
