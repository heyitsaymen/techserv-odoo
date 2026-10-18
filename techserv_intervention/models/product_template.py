from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    create_intervention = fields.Boolean(
        string='Create an Intervention',
        help="When a sales order containing this product is confirmed, an intervention "
             "is automatically created and the technical team is notified.")
