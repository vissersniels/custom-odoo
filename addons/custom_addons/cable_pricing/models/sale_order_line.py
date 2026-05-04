import re

from odoo import api, fields, models

from .constants import APPLICATION_SELECTION


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    cable_pn = fields.Char(string='Cable P/N', copy=False)
    cable_connector_combined = fields.Char(
        string='Connector Key',
        compute='_compute_cable_pricing_details',
    )
    cable_option_code = fields.Char(
        string='Option Code',
        compute='_compute_cable_pricing_details',
    )
    cable_ac_coding = fields.Char(
        string='Cable AC Code',
        compute='_compute_cable_pricing_details',
    )
    cable_length_m = fields.Float(
        string='Cable Length (m)',
        compute='_compute_cable_pricing_details',
        digits='Product Unit of Measure',
    )
    cable_category = fields.Selection(
        selection=APPLICATION_SELECTION,
        string='Cable Category',
        compute='_compute_cable_pricing_details',
    )
    cable_purchase_price = fields.Monetary(
        string='Cable Purchase Price',
        currency_field='currency_id',
        compute='_compute_cable_pricing_details',
    )
    cable_sales_factor = fields.Float(
        string='Cable Sales Factor',
        compute='_compute_cable_pricing_details',
        digits=(16, 6),
    )
    cable_sales_price = fields.Monetary(
        string='Cable Sales Price',
        currency_field='currency_id',
        compute='_compute_cable_pricing_details',
    )
    cable_tier = fields.Char(
        string='Cable Tier',
        compute='_compute_cable_pricing_details',
    )
    cable_pricing_error = fields.Char(
        string='Cable Pricing Error',
        compute='_compute_cable_pricing_details',
    )
    cable_manual_price = fields.Boolean(
        string='Cable Manual Price Override',
        copy=False,
        default=False,
    )

    @api.model
    def _parse_cable_pn(self, pn):
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

    def _get_cable_pn_candidate(self):
        self.ensure_one()
        if self.product_id:
            for candidate in (self.product_id.default_code, self.product_id.name):
                if candidate:
                    parsed = self._parse_cable_pn(candidate)
                    if parsed:
                        return candidate, False

        if self.cable_pn:
            return self.cable_pn, True

        return False, False

    def _reset_cable_pricing_details(self):
        for line in self:
            line.cable_connector_combined = False
            line.cable_option_code = False
            line.cable_ac_coding = False
            line.cable_length_m = 0.0
            line.cable_category = False
            line.cable_purchase_price = 0.0
            line.cable_sales_factor = 0.0
            line.cable_sales_price = 0.0
            line.cable_tier = False
            line.cable_pricing_error = False

    def _get_cable_pricing_payload(self):
        self.ensure_one()

        pn_candidate, is_manual_pn = self._get_cable_pn_candidate()
        parsed = self._parse_cable_pn(pn_candidate)
        if not parsed:
            if is_manual_pn:
                return {'error': 'Cable P/N format must be: BASE SUFFIX OPTION AC_CODE LENGTH_MM.'}
            return {'skip': True}

        connector = self.env['cable.connector.price'].search([
            ('connector_combined', '=', parsed['connector_combined']),
            ('active', '=', True),
        ], limit=1)
        if not connector:
            return {
                'parsed': parsed,
                'error': f'No connector pricing found for {parsed["connector_combined"]}.',
            }

        cable = self.env['cable.cable.price'].search([
            ('ac_coding', '=', parsed['ac_coding']),
            ('active', '=', True),
        ], limit=1)
        if not cable:
            return {
                'parsed': parsed,
                'error': f'No cable pricing found for AC coding {parsed["ac_coding"]}.',
            }

        pricing = self.env['cable.connector.price'].compute_quote_price(
            connector_combined=parsed['connector_combined'],
            ac_coding=parsed['ac_coding'],
            qty=self.product_uom_qty,
            length_m=parsed['length_m'],
            category=connector.application,
        )

        return {
            'parsed': parsed,
            'category': connector.application,
            'pricing': pricing,
        }

    @api.depends('cable_pn', 'product_id', 'product_id.default_code', 'product_id.name', 'product_uom_qty')
    def _compute_cable_pricing_details(self):
        for line in self:
            line._reset_cable_pricing_details()
            if line.display_type or (not line.cable_pn and not line.product_id):
                continue

            payload = line._get_cable_pricing_payload()
            if payload.get('skip'):
                continue

            parsed = payload.get('parsed') or {}
            line.cable_connector_combined = parsed.get('connector_combined')
            line.cable_option_code = parsed.get('option_code')
            line.cable_ac_coding = parsed.get('ac_coding')
            line.cable_length_m = parsed.get('length_m', 0.0)

            if payload.get('error'):
                line.cable_pricing_error = payload['error']
                continue

            pricing = payload['pricing']
            line.cable_category = payload['category']
            line.cable_purchase_price = pricing['purchase_price']
            line.cable_sales_factor = pricing['sales_factor']
            line.cable_sales_price = pricing['sales_price']
            line.cable_tier = pricing['tier']

    @api.depends('product_id', 'product_uom', 'product_uom_qty', 'cable_pn', 'cable_manual_price')
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if (
                not line.order_id
                or line.display_type
                or line.cable_pricing_error
                or line.qty_invoiced > 0
                or not line.cable_sales_price
                or line.cable_manual_price
            ):
                continue

            line = line.with_context(sale_write_from_compute=True, cable_auto_pricing_update=True)
            line.price_unit = line.cable_sales_price
            line.technical_price_unit = line.cable_sales_price

    @api.onchange('product_id', 'cable_pn')
    def _onchange_reset_cable_manual_price(self):
        for line in self:
            line.cable_manual_price = False

    @api.onchange('product_id', 'cable_pn', 'product_uom_qty')
    def _onchange_cable_pricing(self):
        warning = False
        for line in self:
            if line.display_type:
                continue

            if not line.product_id and not line.cable_pn:
                continue

            if line.cable_pricing_error:
                # Keep non-cable products silent, but show format errors for manual cable P/N input.
                if not line.cable_pn:
                    continue
                warning = {
                    'title': 'Cable Pricing',
                    'message': line.cable_pricing_error,
                }
                continue

            if not line.cable_sales_price:
                continue

            if line.cable_manual_price:
                continue

            line.price_unit = line.cable_sales_price
            line.technical_price_unit = line.cable_sales_price

        if warning:
            return {'warning': warning}

    def write(self, vals):
        result = super().write(vals)

        if self.env.context.get('cable_auto_pricing_update'):
            return result

        if 'product_id' in vals or 'cable_pn' in vals:
            self.with_context(cable_auto_pricing_update=True).write({'cable_manual_price': False})
            return result

        if 'price_unit' in vals:
            lines = self.filtered(lambda line: line.cable_sales_price and line.currency_id)
            manual_lines = lines.filtered(
                lambda line: not line.currency_id.is_zero(line.price_unit - line.cable_sales_price)
            )
            auto_lines = lines - manual_lines

            if manual_lines:
                manual_lines.with_context(cable_auto_pricing_update=True).write({'cable_manual_price': True})
            if auto_lines:
                auto_lines.with_context(cable_auto_pricing_update=True).write({'cable_manual_price': False})

        return result
