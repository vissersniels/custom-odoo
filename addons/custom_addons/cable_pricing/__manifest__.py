{
    'name': 'Cable Pricing',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Master data and tier logic for cable quote pricing',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/cable_pricing_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
