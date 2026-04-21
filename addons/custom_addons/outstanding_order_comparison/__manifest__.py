{
    'name': 'Outstanding Order Comparison',
    'version': '18.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Adds an Outstanding Order Comparison menu item to the Purchase app.',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/outstanding_order_comparison_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'outstanding_order_comparison/static/src/js/drag_drop_binary_field.js',
            'outstanding_order_comparison/static/src/xml/drag_drop_binary_field.xml',
            'outstanding_order_comparison/static/src/scss/outstanding_order_comparison.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
