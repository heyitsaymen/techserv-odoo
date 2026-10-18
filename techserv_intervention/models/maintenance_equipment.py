from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    """Équipement installé chez un client.

    On étend le modèle standard ``maintenance.equipment`` au lieu de créer un
    nouveau modèle : on récupère le chatter, l'historique des demandes, les
    vues kanban/liste et la contrainte d'unicité du numéro de série
    (``_serial_no = models.Constraint('unique(serial_no)', ...)``) déjà
    présente en standard dans Odoo 19.
    """
    _inherit = 'maintenance.equipment'

    # Le champ standard ``partner_id`` désigne le FOURNISSEUR de l'équipement :
    # on ajoute donc un champ distinct pour le client chez qui il est installé.
    customer_id = fields.Many2one(
        'res.partner', string='Customer', tracking=True, index='btree_not_null',
        check_company=True, help="Customer where the equipment is installed.")
    product_id = fields.Many2one(
        'product.product', string='Product', tracking=True, check_company=True,
        help="Product (model) of the installed equipment.")

    # Champs standards réutilisés : on active seulement le suivi (chatter)
    serial_no = fields.Char(tracking=True)
    warranty_date = fields.Date(tracking=True)
    # ``effective_date`` (standard) sert de date d'installation / mise en service
    effective_date = fields.Date(string='Installation Date', tracking=True)

    # Champ calculé NON stocké : sa valeur dépend de la date du jour, un champ
    # stocké deviendrait faux le lendemain sans que rien ne le recalcule.
    is_under_warranty = fields.Boolean(
        string='Under Warranty', compute='_compute_is_under_warranty',
        search='_search_is_under_warranty')

    @api.depends('warranty_date')
    def _compute_is_under_warranty(self):
        today = fields.Date.context_today(self)
        for equipment in self:
            equipment.is_under_warranty = equipment._is_under_warranty_at(today)

    def _search_is_under_warranty(self, operator, value):
        # En Odoo 19, l'ORM normalise les recherches sur un booléen en
        # ('is_under_warranty', 'in', {True}) ; il gère lui-même la négation
        # ('not in') si on retourne NotImplemented.
        if operator != 'in':
            return NotImplemented
        today = fields.Date.context_today(self)
        under_warranty = [('warranty_date', '>=', today)]
        if True in value and False in value:
            return []
        if True in value:
            return under_warranty
        return ['|', ('warranty_date', '=', False), ('warranty_date', '<', today)]

    def _is_under_warranty_at(self, date):
        """Vrai si l'équipement est couvert par la garantie à la date donnée."""
        self.ensure_one()
        return bool(self.warranty_date and date and self.warranty_date >= date)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Pré-remplit le nom de l'équipement avec le nom du produit
        if self.product_id and not self.name:
            self.name = self.product_id.name

    def action_new_intervention(self):
        """Bouton « Nouvelle intervention » : ouvre le formulaire d'une demande
        avec le client et l'équipement pré-remplis par le contexte (default_...)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("New Intervention"),
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_equipment_id': self.id,
                'default_customer_id': self.customer_id.id,
                'default_company_id': (self.company_id or self.env.company).id,
                'default_name': self.env._("Intervention on %s", self.display_name),
            },
        }
