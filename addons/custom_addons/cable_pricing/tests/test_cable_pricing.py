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
