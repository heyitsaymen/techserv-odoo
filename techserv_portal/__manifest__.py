{
    'name': 'TechServ - Customer Portal',
    'version': '19.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': "Le client consulte ses interventions et signe le bon d'intervention en ligne",
    'description': """
Bonus TechServ : extension du portail client standard (module portal).
Séparé de techserv_intervention pour rester optionnel.
    """,
    'author': 'Aymen',
    'license': 'LGPL-3',
    'depends': [
        'techserv_intervention',
        'portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/techserv_portal_security.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
}
