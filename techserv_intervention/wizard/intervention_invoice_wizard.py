from odoo import fields, models
from odoo.exceptions import UserError


class TechservInterventionInvoiceWizard(models.TransientModel):
    """Facturation groupée des interventions terminées : une facture par
    intervention ou une facture par client."""
    _name = 'techserv.intervention.invoice.wizard'
    _description = 'Invoice Interventions'

    def _default_intervention_ids(self):
        Intervention = self.env['maintenance.request']
        if self.env.context.get('active_model') == 'maintenance.request' and self.env.context.get('active_ids'):
            interventions = Intervention.browse(self.env.context['active_ids'])
        else:
            # Ouvert depuis le menu : toutes les interventions terminées non facturées
            interventions = Intervention.search([('techserv_state', '=', 'done'), ('invoice_id', '=', False)])
        return interventions.filtered(lambda r: r.techserv_state == 'done' and not r.invoice_id)

    intervention_ids = fields.Many2many(
        'maintenance.request', string='Interventions', default=_default_intervention_ids,
        domain="[('techserv_state', '=', 'done'), ('invoice_id', '=', False)]")
    grouping = fields.Selection([
        ('intervention', 'One invoice per intervention'),
        ('customer', 'One invoice per customer'),
    ], string='Grouping', default='customer', required=True)

    def action_create_invoices(self):
        self.ensure_one()
        interventions = self.intervention_ids
        if not interventions:
            raise UserError(self.env._("There is no intervention to invoice."))
        invoices = interventions._techserv_create_invoices(grouping=self.grouping)
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) == 1:
            action.update(views=[(self.env.ref('account.view_move_form').id, 'form')], res_id=invoices.id)
        else:
            action['domain'] = [('id', 'in', invoices.ids)]
        return action
