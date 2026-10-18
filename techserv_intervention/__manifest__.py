{
    'name': 'TechServ - Interventions',
    'version': '19.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': "Parc client, interventions, planification, clôture et facturation",
    'description': """
Gestion des interventions TechServ (installation et dépannage de climatiseurs,
groupes électrogènes et pompes), construite en étendant les modules standards :
Maintenance, Employés, Flotte, Ventes, Inventaire et Facturation.
    """,
    'author': 'Aymen',
    'license': 'LGPL-3',
    'depends': [
        'maintenance',
        'hr',
        'product',
    ],
    'data': [
        'data/ir_sequence_data.xml',
        'data/maintenance_stage_data.xml',
        'views/maintenance_equipment_views.xml',
        'views/maintenance_request_views.xml',
    ],
    'demo': [
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
}
