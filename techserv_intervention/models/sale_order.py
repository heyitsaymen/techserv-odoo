from odoo import api, fields, models
from odoo.tools import plaintext2html


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    intervention_ids = fields.One2many('maintenance.request', 'sale_order_id', string='Interventions')
    # Compteur non stocké : toujours à jour, calculé seulement à l'affichage
    intervention_count = fields.Integer(string='Intervention Count', compute='_compute_intervention_count')

    @api.depends('intervention_ids')
    def _compute_intervention_count(self):
        for order in self:
            order.intervention_count = len(order.intervention_ids)

    def action_confirm(self):
        """Confirmation du devis : on appelle d'abord le standard (super) pour ne
        rien changer au flux de vente, puis on crée les interventions."""
        res = super().action_confirm()
        self._create_techserv_interventions()
        return res

    def _create_techserv_interventions(self):
        Intervention = self.env['maintenance.request']
        # Une ligne déjà traitée (devis annulé puis reconfirmé) ne recrée pas d'intervention
        done_lines = Intervention.sudo().search([('sale_line_id', 'in', self.order_line.ids)]).sale_line_id
        vals_list = []
        for order in self:
            lines = order.order_line.filtered(
                lambda line: line.product_id.create_intervention and not line.display_type and line not in done_lines)
            vals_list += [order._prepare_techserv_intervention_values(line) for line in lines]
        if not vals_list:
            return Intervention
        interventions = Intervention.create(vals_list)
        for intervention in interventions:
            intervention._techserv_notify_team(
                summary=self.env._("New intervention to plan"),
                note=self.env._("Created from the confirmed sales order %s.", intervention.sale_order_id.name),
            )
        return interventions

    def _prepare_techserv_intervention_values(self, line):
        self.ensure_one()
        return {
            'name': f"{line.product_id.name} - {self.name}",
            'customer_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'sale_order_id': self.id,
            'sale_line_id': line.id,
            'description': plaintext2html(line.name or ''),
            'maintenance_type': 'corrective',
        }

    def action_view_interventions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {'default_sale_order_id': self.id, 'default_customer_id': self.partner_id.id}
        if len(self.intervention_ids) == 1:
            action.update(view_mode='form', views=[(False, 'form')], res_id=self.intervention_ids.id)
        return action
