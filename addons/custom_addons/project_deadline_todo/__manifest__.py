{
    'name': 'Project Deadline To-Do',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Automatically creates To-Dos for assignees when a task deadline is approaching or overdue',
    'depends': ['project', 'project_todo'],
    'data': [
        'data/cron.xml',
    ],
    'installable': True,
    'application': False,
}
