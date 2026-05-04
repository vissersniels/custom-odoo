from odoo import fields, models

from .constants import APPLICATION_SELECTION


class CableCablePrice(models.Model):
    _name = 'cable.cable.price'
    _description = 'Cable Price Per Meter'
    _order = 'ac_coding'
    _rec_name = 'ac_coding'

    ac_coding = fields.Char(required=True, index=True, copy=False)
    description = fields.Char()
    poles = fields.Integer()
    application = fields.Selection(
        selection=APPLICATION_SELECTION,
        required=True,
        default='signal',
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    price_per_meter = fields.Monetary(currency_field='currency_id', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('ac_coding_unique', 'unique(ac_coding)', 'AC coding must be unique.'),
    ]
