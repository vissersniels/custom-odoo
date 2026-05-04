{
    'name': 'Cable Pricing',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Master data and tier logic for cable quote pricing',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/cable_price_break_data.xml',
        'data/cable_connector_price_data.xml',
        'data/cable_cable_price_data.xml',
        'views/cable_pricing_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
