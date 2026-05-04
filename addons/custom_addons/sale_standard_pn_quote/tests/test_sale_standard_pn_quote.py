from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install')
class TestSaleStandardPnQuote(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.connector_model = cls.env['cable.connector.price']
        cls.cable_model = cls.env['cable.cable.price']

        cls.partner = cls.env['res.partner'].create({'name': 'Standard PN Customer'})

        cls.connector = cls.connector_model.create({
            'connector_combined': 'X999ABC',
            'series': 'Test Series',
            'application': 'signal',
            'price_1_49': 2.40,
            'price_50_299': 2.20,
            'price_300_999': 2.00,
            'price_1000_4999': 1.90,
            'price_5000_9999': 1.80,
            'price_10000_19999': 1.70,
            'price_20000_49999': 1.60,
            'price_50000_plus': 1.50,
        })
        cls.cable = cls.cable_model.create({
            'ac_coding': 'ZZ',
            'description': 'Test cable',
            'poles': 2,
            'application': 'signal',
            'price_per_meter': 1.00,
        })

    def test_standard_pn_line_computes_without_product(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.standard.pn.line'].create({
            'order_id': order.id,
            'standard_pn': 'X999AB C 00 ZZ 0100',
            'quantity': 10,
        })

        expected = self.connector_model.compute_quote_price(
            connector_combined='X999ABC',
            ac_coding='ZZ',
            qty=10,
            length_m=0.1,
            category='signal',
        )

        self.assertFalse(line.pricing_error)
        self.assertEqual(line.connector_combined, 'X999ABC')
        self.assertEqual(line.ac_coding, 'ZZ')
        self.assertAlmostEqual(line.length_m, 0.1, places=6)
        self.assertAlmostEqual(line.price_unit, expected['sales_price'], places=6)
        self.assertAlmostEqual(line.price_subtotal, line.quantity * line.price_unit, places=6)

    def test_invalid_standard_pn_sets_error(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.standard.pn.line'].create({
            'order_id': order.id,
            'standard_pn': 'INVALID-CODE',
            'quantity': 2,
        })

        self.assertTrue(line.pricing_error)
        self.assertAlmostEqual(line.price_unit, 0.0, places=6)
        self.assertAlmostEqual(line.price_subtotal, 0.0, places=6)

    def test_selected_price_break_category_is_used(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        line = self.env['sale.order.standard.pn.line'].create({
            'order_id': order.id,
            'standard_pn': 'X999AB C 00 ZZ 0100',
            'quantity': 10,
            'price_break_category': 'power',
        })

        expected = self.connector_model.compute_quote_price(
            connector_combined='X999ABC',
            ac_coding='ZZ',
            qty=10,
            length_m=0.1,
            category='power',
        )

        self.assertFalse(line.pricing_error)
        self.assertEqual(line.category, 'power')
        self.assertAlmostEqual(line.sales_factor, expected['sales_factor'], places=6)
        self.assertAlmostEqual(line.price_unit, expected['sales_price'], places=6)

    def test_order_total_includes_standard_pn_amount(self):
        order = self.env['sale.order'].create({'partner_id': self.partner.id})
        self.env['sale.order.standard.pn.line'].create({
            'order_id': order.id,
            'standard_pn': 'X999AB C 00 ZZ 0100',
            'quantity': 3,
        })

        self.assertGreater(order.standard_pn_amount_untaxed, 0.0)
        self.assertAlmostEqual(order.standard_pn_amount_total, order.standard_pn_amount_untaxed, places=6)
        self.assertAlmostEqual(
            order.amount_total_with_standard_pn,
            order.amount_total + order.standard_pn_amount_untaxed,
            places=6,
        )
