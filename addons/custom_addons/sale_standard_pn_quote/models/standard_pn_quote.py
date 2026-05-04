import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


APPLICATION_SELECTION = [
    ('signal', 'Signal'),
    ('pur', 'PUR'),
    ('power', 'Power'),
    ('ea', 'E&A'),
]

PRICE_BREAK_SELECTION = [
    ('signal', 'Signal'),
    ('power', 'Power'),
    ('ea', 'E&A'),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    standard_pn_line_ids = fields.One2many(
        'sale.order.standard.pn.line',
        'order_id',
        string='Standard PN Lines',
        copy=True,
    )
    standard_pn_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        currency_field='currency_id',
        compute='_compute_standard_pn_totals',
        store=True,
    )
    standard_pn_amount_total = fields.Monetary(
        string='Total',
        currency_field='currency_id',
        compute='_compute_standard_pn_totals',
        store=True,
    )
    amount_total_with_standard_pn = fields.Monetary(
        string='Total Including Standard PN',
        currency_field='currency_id',
        compute='_compute_standard_pn_totals',
        store=True,
    )
    standard_pn_has_errors = fields.Boolean(
        string='Standard PN Has Errors',
        compute='_compute_standard_pn_totals',
        store=True,
    )
    standard_pn_line_count = fields.Integer(
        string='Standard PN Line Count',
        compute='_compute_standard_pn_totals',
        store=True,
    )

    @api.depends('amount_total', 'standard_pn_line_ids.price_subtotal', 'standard_pn_line_ids.pricing_error')
    def _compute_standard_pn_totals(self):
        for order in self:
            standard_subtotal = sum(order.standard_pn_line_ids.mapped('price_subtotal'))
            order.standard_pn_amount_untaxed = standard_subtotal
            order.standard_pn_amount_total = standard_subtotal
            order.amount_total_with_standard_pn = order.amount_total + standard_subtotal
            order.standard_pn_has_errors = any(order.standard_pn_line_ids.mapped('pricing_error'))
            order.standard_pn_line_count = len(order.standard_pn_line_ids)


class SaleOrderStandardPnLine(models.Model):
    _name = 'sale.order.standard.pn.line'
    _description = 'Sale Order Standard PN Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='order_id.company_id', readonly=True, store=True)
    currency_id = fields.Many2one(related='order_id.currency_id', readonly=True, store=True)

    standard_pn = fields.Char(string='Standard PN', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0, digits='Product Unit of Measure')
    price_break_category = fields.Selection(
        selection=PRICE_BREAK_SELECTION,
        string='Price Break',
        required=True,
        default='signal',
    )

    connector_combined = fields.Char(string='Connector Key', compute='_compute_pricing', store=True)
    option_code = fields.Char(string='Option Code', compute='_compute_pricing', store=True)
    ac_coding = fields.Char(string='AC Coding', compute='_compute_pricing', store=True)
    length_m = fields.Float(
        string='Length (m)',
        compute='_compute_pricing',
        store=True,
        digits='Product Unit of Measure',
    )
    category = fields.Selection(
        selection=APPLICATION_SELECTION,
        string='Category',
        compute='_compute_pricing',
        store=True,
    )
    tier = fields.Char(string='Tier', compute='_compute_pricing', store=True)

    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        compute='_compute_pricing',
        store=True,
    )
    sales_factor = fields.Float(
        string='Sales Factor',
        compute='_compute_pricing',
        store=True,
        digits=(16, 6),
    )
    price_unit = fields.Monetary(
        string='Unit Price',
        currency_field='currency_id',
        compute='_compute_pricing',
        store=True,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True,
    )
    pricing_error = fields.Char(string='Pricing Error', compute='_compute_pricing', store=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than 0.'))

    @api.model
    def _parse_standard_pn(self, pn):
        if not pn:
            return False

        parts = re.split(r'\s+', pn.strip())
        if len(parts) != 5:
            return False

        connector_base, connector_suffix, option_code, ac_coding, length_mm = parts
        if not length_mm.isdigit():
            return False

        return {
            'connector_combined': f'{connector_base}{connector_suffix}',
            'option_code': option_code,
            'ac_coding': ac_coding,
            'length_m': int(length_mm) / 1000,
        }

    @api.depends('quantity', 'standard_pn', 'price_break_category')
    def _compute_pricing(self):
        ConnectorPrice = self.env['cable.connector.price']
        CablePrice = self.env['cable.cable.price']

        for line in self:
            line.connector_combined = False
            line.option_code = False
            line.ac_coding = False
            line.length_m = 0.0
            line.category = line.price_break_category
            line.tier = False
            line.purchase_price = 0.0
            line.sales_factor = 0.0
            line.price_unit = 0.0
            line.pricing_error = False

            parsed = line._parse_standard_pn(line.standard_pn)
            if not parsed:
                line.pricing_error = _('Standard PN format must be: BASE SUFFIX OPTION AC_CODE LENGTH_MM.')
                continue

            line.connector_combined = parsed['connector_combined']
            line.option_code = parsed['option_code']
            line.ac_coding = parsed['ac_coding']
            line.length_m = parsed['length_m']

            if line.quantity <= 0:
                line.pricing_error = _('Quantity must be greater than 0.')
                continue

            connector = ConnectorPrice.search([
                ('connector_combined', '=', parsed['connector_combined']),
                ('active', '=', True),
            ], limit=1)
            if not connector:
                line.pricing_error = _('No connector pricing found for %s.') % parsed['connector_combined']
                continue

            cable = CablePrice.search([
                ('ac_coding', '=', parsed['ac_coding']),
                ('active', '=', True),
            ], limit=1)
            if not cable:
                line.pricing_error = _('No cable pricing found for AC coding %s.') % parsed['ac_coding']
                continue

            try:
                pricing = ConnectorPrice.compute_quote_price(
                    connector_combined=parsed['connector_combined'],
                    ac_coding=parsed['ac_coding'],
                    qty=line.quantity,
                    length_m=parsed['length_m'],
                    category=line.price_break_category,
                )
            except ValidationError as error:
                line.pricing_error = error.args[0]
                continue

            line.category = line.price_break_category
            line.tier = pricing['tier']
            line.purchase_price = pricing['purchase_price']
            line.sales_factor = pricing['sales_factor']
            line.price_unit = pricing['sales_price']

    @api.depends('quantity', 'price_unit', 'pricing_error')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit if not line.pricing_error else 0.0
