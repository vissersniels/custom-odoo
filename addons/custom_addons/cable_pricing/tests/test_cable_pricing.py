from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install')
class TestCablePricing(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connector_model = cls.env['cable.connector.price']
        cls.cable_model = cls.env['cable.cable.price']
        cls.break_model = cls.env['cable.price.break']

        cls.connector_model.search([]).unlink()
        cls.cable_model.search([]).unlink()
        cls.break_model.search([]).unlink()
        cls.break_a = cls.break_model.create({
            'tier': 'A',
            'moq': 10,
            'signal_factor': 1.00,
            'pur_factor': 1.20,
            'power_factor': 1.30,
            'ea_factor': 1.10,
        })
        cls.break_b = cls.break_model.create({
            'tier': 'B',
            'moq': 50,
            'signal_factor': 0.95,
            'pur_factor': 1.10,
            'power_factor': 1.20,
            'ea_factor': 1.05,
        })
        cls.break_c = cls.break_model.create({
            'tier': 'C',
            'moq': 300,
            'signal_factor': 0.90,
            'pur_factor': 1.00,
            'power_factor': 1.10,
            'ea_factor': 1.00,
        })

        cls.connector = cls.connector_model.create({
            'connector_combined': 'Z209BGP',
            'series': 'Z209BG',
            'application': 'signal',
            'price_1_49': 2.05,
            'price_50_299': 1.95,
            'price_300_999': 1.85,
            'price_1000_4999': 1.75,
            'price_5000_9999': 1.65,
            'price_10000_19999': 1.55,
            'price_20000_49999': 1.45,
            'price_50000_plus': 1.35,
        })
        cls.cable = cls.cable_model.create({
            'ac_coding': 'A0',
            'description': 'Signal cable A0',
            'poles': 2,
            'application': 'signal',
            'price_per_meter': 0.8,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cable Pricing Customer',
        })
        unit_uom = cls.env.ref('uom.product_uom_unit')
        cls.product = cls.env['product.product'].create({
            'name': 'Cable Assembly',
            'default_code': 'Z209BG P 00 A0 0150',
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': False,
            'uom_id': unit_uom.id,
            'uom_po_id': unit_uom.id,
            'list_price': 99.0,
            'taxes_id': [(5, 0, 0)],
        })

    def test_connector_price_tier_boundaries(self):
        self.assertEqual(self.connector._get_price_at_qty(1), 2.05)
        self.assertEqual(self.connector._get_price_at_qty(49), 2.05)
        self.assertEqual(self.connector._get_price_at_qty(50), 1.95)
        self.assertEqual(self.connector._get_price_at_qty(299), 1.95)
        self.assertEqual(self.connector._get_price_at_qty(300), 1.85)
        self.assertEqual(self.connector._get_price_at_qty(1000), 1.75)
        self.assertEqual(self.connector._get_price_at_qty(5000), 1.65)
        self.assertEqual(self.connector._get_price_at_qty(10000), 1.55)
        self.assertEqual(self.connector._get_price_at_qty(20000), 1.45)
        self.assertEqual(self.connector._get_price_at_qty(50000), 1.35)

    def test_price_break_factor_selection(self):
        self.assertEqual(self.break_model._get_break_for_qty(1).tier, 'A')
        self.assertEqual(self.break_model._get_break_for_qty(10).tier, 'A')
        self.assertEqual(self.break_model._get_break_for_qty(120).tier, 'B')
        self.assertEqual(self.break_model._get_break_for_qty(1000).tier, 'C')

        self.assertEqual(self.break_model._get_factor(10, 'signal'), 1.00)
        self.assertEqual(self.break_model._get_factor(60, 'signal'), 0.95)
        self.assertEqual(self.break_model._get_factor(350, 'signal'), 0.90)
        self.assertEqual(self.break_model._get_factor(60, 'power'), 1.20)

    def test_compute_quote_price_matches_formula(self):
        result = self.connector_model.compute_quote_price(
            connector_combined='Z209BGP',
            ac_coding='A0',
            qty=10,
            length_m=0.150,
            category='signal',
        )

        self.assertAlmostEqual(result['connector_price'], 2.05, places=6)
        self.assertAlmostEqual(result['cable_price'], 0.12, places=6)
        self.assertAlmostEqual(result['purchase_price'], 2.17, places=6)
        self.assertAlmostEqual(result['sales_price'], 2.17, places=6)
        self.assertEqual(result['tier'], 'A')

    def test_parse_cable_pn(self):
        parsed = self.env['sale.order.line']._parse_cable_pn('Z209BG P 00 A0 0150')
        self.assertEqual(parsed['connector_combined'], 'Z209BGP')
        self.assertEqual(parsed['option_code'], '00')
        self.assertEqual(parsed['ac_coding'], 'A0')
        self.assertAlmostEqual(parsed['length_m'], 0.150, places=6)

    def test_sale_order_line_applies_cable_price_on_create(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 10,
        })

        self.assertFalse(line.cable_pricing_error)
        self.assertEqual(line.cable_tier, 'A')
        self.assertEqual(line.cable_connector_combined, 'Z209BGP')
        self.assertEqual(line.cable_ac_coding, 'A0')
        self.assertAlmostEqual(line.cable_length_m, 0.150, places=6)
        self.assertAlmostEqual(line.cable_purchase_price, 2.17, places=6)
        self.assertAlmostEqual(line.price_unit, 2.17, places=6)

    def test_sale_order_line_recomputes_cable_price_when_qty_changes(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 10,
        })

        line.write({'product_uom_qty': 60})

        self.assertFalse(line.cable_pricing_error)
        self.assertEqual(line.cable_tier, 'B')
        self.assertAlmostEqual(line.cable_purchase_price, 2.07, places=6)
        self.assertAlmostEqual(line.cable_sales_factor, 0.95, places=6)
        self.assertAlmostEqual(line.price_unit, 1.97, places=2)

    def test_non_cable_product_code_keeps_standard_pricing_without_error(self):
        unit_uom = self.env.ref('uom.product_uom_unit')
        non_cable_product = self.env['product.product'].create({
            'name': 'Standard Product',
            'default_code': 'STANDARD-001',
            'type': 'consu',
            'sale_ok': True,
            'purchase_ok': False,
            'uom_id': unit_uom.id,
            'uom_po_id': unit_uom.id,
            'list_price': 42.0,
            'taxes_id': [(5, 0, 0)],
        })

        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': non_cable_product.id,
            'product_uom_qty': 10,
        })

        self.assertFalse(line.cable_pricing_error)
        self.assertEqual(line.cable_sales_price, 0.0)
        self.assertFalse(line.cable_tier)
        self.assertAlmostEqual(line.price_unit, 42.0, places=6)

    def test_manual_price_override_is_preserved_after_qty_change(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'product_uom_qty': 10,
        })

        line.write({'price_unit': 3.33})
        line.write({'product_uom_qty': 60})

        self.assertTrue(line.cable_manual_price)
        self.assertAlmostEqual(line.price_unit, 3.33, places=2)
