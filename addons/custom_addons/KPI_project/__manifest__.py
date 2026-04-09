{
    'name': 'KPI Project',
    'version': '18.0.1.0.0',
    'category': 'Project Management',
    'depends': ['project'],
    'data': [
        'security/ir.model.access.csv',
        'data/kpi_cron.xml',
        'views/kpi_views.xml',
        'views/kpi_actions.xml',
        'views/KPI_dashboard_project_menu.xml',
    ],
    'installable': True,
    'application': False,
}