from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # One2many inverse de maintenance.equipment.customer_id. Il sert au filtre
    # « A des équipements » : un champ One2many est cherchable
    # ([('equipment_ids', '!=', False)]), alors qu'un compteur non stocké ne l'est pas.
    equipment_ids = fields.One2many('maintenance.equipment', 'customer_id', string='Equipment')
    equipment_count = fields.Integer(string='Equipment Count', compute='_compute_techserv_counts')
    intervention_count = fields.Integer(string='Intervention Count', compute='_compute_techserv_counts')

    def _compute_techserv_counts(self):
        # child_of : une société voit aussi les équipements de ses contacts (sites, agences...)
        Equipment = self.env['maintenance.equipment']
        Intervention = self.env['maintenance.request']
        for partner in self:
            if not partner.id:
                partner.equipment_count = partner.intervention_count = 0
                continue
            partner.equipment_count = Equipment.search_count([('customer_id', 'child_of', partner.id)])
            partner.intervention_count = Intervention.search_count([('customer_id', 'child_of', partner.id)])

    def action_view_equipment(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_action')
        action['domain'] = [('customer_id', 'child_of', self.id)]
        action['context'] = {'default_customer_id': self.id}
        return action

    def action_view_interventions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
        action['domain'] = [('customer_id', 'child_of', self.id)]
        action['context'] = {'default_customer_id': self.id}
        return action
