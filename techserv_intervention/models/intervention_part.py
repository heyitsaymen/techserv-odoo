from odoo import fields, models


class TechservInterventionPart(models.Model):
    """Pièce utilisée lors d'une intervention.

    Seul nouveau modèle persistant du module. Pourquoi ne pas lire directement
    les mouvements de stock ? Les techniciens ne sont pas utilisateurs de
    l'Inventaire : ils n'ont pas le droit de lire ``stock.move``. Cette ligne
    « métier » est lisible par le technicien, le portail client, le bon
    d'intervention et la facturation ; le mouvement de stock standard
    (``move_id``) reste la vérité côté inventaire.
    """
    _name = 'techserv.intervention.part'
    _description = 'Intervention Part'
    _order = 'intervention_id, id'
    _check_company_auto = True

    intervention_id = fields.Many2one(
        'maintenance.request', string='Intervention', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='intervention_id.company_id', store=True, index=True)
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, check_company=True,
        domain="[('type', '=', 'consu')]")
    quantity = fields.Float(string='Quantity', digits='Product Unit', default=1.0, required=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id', string='Unit')
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False)

    _quantity_positive = models.Constraint(
        'CHECK(quantity > 0)',
        "The quantity of a part must be positive.",
    )
