from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import APPLICATION_FACTOR_FIELD_MAP


class CablePriceBreak(models.Model):
    _name = 'cable.price.break'
    _description = 'Cable Price Break'
    _order = 'moq asc'

    tier = fields.Selection(
        selection=[
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D'),
            ('E', 'E'),
            ('F', 'F'),
            ('G', 'G'),
            ('H', 'H'),
        ],
        required=True,
        copy=False,
    )
    moq = fields.Integer(required=True)
    signal_factor = fields.Float(required=True, default=1.0, digits=(16, 6))
    pur_factor = fields.Float(required=True, default=1.0, digits=(16, 6))
    power_factor = fields.Float(required=True, default=1.0, digits=(16, 6))
    ea_factor = fields.Float(required=True, default=1.0, digits=(16, 6))
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('tier_unique', 'unique(tier)', 'Tier must be unique.'),
    ]

    @api.constrains('moq')
    def _check_moq(self):
        for record in self:
            if record.moq <= 0:
                raise ValidationError('MOQ must be strictly positive.')

    def _factor_for_category(self, category):
        self.ensure_one()
        category = (category or '').strip().lower()
        factor_field = APPLICATION_FACTOR_FIELD_MAP.get(category)
        if not factor_field:
            raise ValidationError(
                'Unknown category. Expected one of: signal, pur, power, ea.'
            )
        return self[factor_field]

    @api.model
    def _get_break_for_qty(self, qty):
        qty = max(int(qty or 0), 1)
        price_break = self.search([
            ('active', '=', True),
            ('moq', '<=', qty),
        ], order='moq desc', limit=1)
        if price_break:
            return price_break
        return self.search([('active', '=', True)], order='moq asc', limit=1)

    @api.model
    def _get_factor(self, qty, category):
        price_break = self._get_break_for_qty(qty)
        if not price_break:
            return 1.0
        return price_break._factor_for_category(category)
