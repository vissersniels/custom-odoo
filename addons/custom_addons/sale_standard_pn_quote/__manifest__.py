{
    'name': 'Sale Standard PN Quote',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Quote with Standard PN lines without product records',
    'depends': ['sale_management', 'cable_pricing'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/sale_report_templates.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
