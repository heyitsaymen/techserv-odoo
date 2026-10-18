from odoo import fields, models

# États techniques d'une intervention, indépendants du libellé des étapes.
TECHSERV_STATES = [
    ('received', 'Request Received'),
    ('planned', 'Planned'),
    ('in_progress', 'In Progress'),
    ('done', 'Done'),
    ('invoiced', 'Invoiced'),
    ('cancel', 'Cancelled'),
]


class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    # Les règles métier (annulation, facturation...) testent cet état et non le
    # nom de l'étape : l'utilisateur peut renommer ou traduire les étapes sans
    # casser le code.
    techserv_state = fields.Selection(
        TECHSERV_STATES, string='TechServ State', index=True,
        help="Technical state used by the TechServ business rules.")
