from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .constants import APPLICATION_SELECTION


class CableConnectorPrice(models.Model):
    _name = 'cable.connector.price'
    _description = 'Cable Connector Price'
    _order = 'connector_combined'
    _rec_name = 'connector_combined'

    connector_combined = fields.Char(required=True, index=True, copy=False)
    series = fields.Char()
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
    active = fields.Boolean(default=True)

    price_1_49 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_50_299 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_300_999 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_1000_4999 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_5000_9999 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_10000_19999 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_20000_49999 = fields.Monetary(currency_field='currency_id', default=0.0)
    price_50000_plus = fields.Monetary(currency_field='currency_id', default=0.0)

    _sql_constraints = [
        ('connector_combined_unique', 'unique(connector_combined)', 'Connector code must be unique.'),
    ]

    def _get_price_at_qty(self, qty):
        self.ensure_one()
        qty = max(int(qty or 0), 1)

        if qty >= 50000:
            return self.price_50000_plus
        if qty >= 20000:
            return self.price_20000_49999
        if qty >= 10000:
            return self.price_10000_19999
        if qty >= 5000:
            return self.price_5000_9999
        if qty >= 1000:
            return self.price_1000_4999
        if qty >= 300:
            return self.price_300_999
        if qty >= 50:
            return self.price_50_299
        return self.price_1_49

    @api.model
    def compute_quote_price(self, connector_combined, ac_coding, qty, length_m, category):
        qty = max(int(qty or 0), 1)
        length_m = max(float(length_m or 0.0), 0.0)
        category = (category or '').strip().lower()

        connector_price = self.search([
            ('connector_combined', '=', connector_combined),
            ('active', '=', True),
        ], limit=1)
        if not connector_price:
            raise ValidationError(f'No connector pricing found for connector code {connector_combined}.')

        cable_price = self.env['cable.cable.price'].search([
            ('ac_coding', '=', ac_coding),
            ('active', '=', True),
        ], limit=1)
        if not cable_price:
            raise ValidationError(f'No cable pricing found for AC coding {ac_coding}.')

        connector_component = connector_price._get_price_at_qty(qty)
        cable_component = cable_price.price_per_meter * length_m
        purchase_price = connector_component + cable_component

        price_break = self.env['cable.price.break']._get_break_for_qty(qty)
        factor = price_break._factor_for_category(category) if price_break else 1.0

        return {
            'connector_price': connector_component,
            'cable_price': cable_component,
            'purchase_price': purchase_price,
            'sales_factor': factor,
            'sales_price': purchase_price * factor,
            'tier': price_break.tier if price_break else False,
        }
