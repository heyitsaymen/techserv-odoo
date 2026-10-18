from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Une facture peut regrouper plusieurs interventions (« une facture par client »)
    intervention_ids = fields.One2many(
        'maintenance.request', 'invoice_id', string='Interventions', readonly=True)
    intervention_count = fields.Integer(string='Intervention Count', compute='_compute_intervention_count')

    @api.depends('intervention_ids')
    def _compute_intervention_count(self):
        for move in self:
            move.intervention_count = len(move.intervention_ids)

    def action_view_interventions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
        action['domain'] = [('invoice_id', '=', self.id)]
        action['context'] = {'create': False}
        return action
