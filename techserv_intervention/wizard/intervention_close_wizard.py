from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class TechservInterventionCloseWizard(models.TransientModel):
    """Clôture en une seule étape : temps passé, pièces utilisées et signature
    du client. Sans signature, la clôture est refusée."""
    _name = 'techserv.intervention.close.wizard'
    _description = 'Close an Intervention'

    def _default_intervention_id(self):
        if self.env.context.get('active_model') == 'maintenance.request':
            return self.env.context.get('active_id')
        return False

    intervention_id = fields.Many2one(
        'maintenance.request', string='Intervention', required=True, default=_default_intervention_id)
    company_id = fields.Many2one(related='intervention_id.company_id')
    # Valeurs proposées (modifiables), calculées depuis l'intervention. Deux méthodes
    # distinctes : si un champ est fourni à la création, Odoo ne recalcule pas les
    # autres champs de la même méthode.
    time_spent = fields.Float(
        string='Time Spent', compute='_compute_time_spent', store=True, readonly=False)
    line_ids = fields.One2many('techserv.intervention.close.wizard.line', 'wizard_id', string='Parts Used')
    signature = fields.Binary(
        string='Customer Signature', compute='_compute_signature', store=True, readonly=False)
    signed_by = fields.Char(string='Signed By', compute='_compute_signed_by', store=True, readonly=False)

    @api.depends('intervention_id')
    def _compute_time_spent(self):
        for wizard in self:
            wizard.time_spent = wizard.intervention_id.duration

    @api.depends('intervention_id')
    def _compute_signature(self):
        # Signature déjà donnée par le client (par exemple en ligne, sur le portail)
        for wizard in self:
            wizard.signature = wizard.intervention_id.customer_signature

    @api.depends('intervention_id')
    def _compute_signed_by(self):
        for wizard in self:
            wizard.signed_by = wizard.intervention_id.signed_by or wizard.intervention_id.customer_id.name

    def action_close(self):
        self.ensure_one()
        intervention = self.intervention_id
        if intervention.techserv_state not in ('planned', 'in_progress'):
            raise UserError(self.env._("Only planned or in progress interventions can be closed."))
        # Contrôle côté serveur : le bouton du formulaire ne suffit pas
        if not self.signature:
            raise UserError(self.env._("The customer must sign the intervention report before closing."))
        if self.time_spent <= 0:
            raise UserError(self.env._("Please enter the time spent."))

        intervention.write({
            'time_spent': self.time_spent,
            'customer_signature': self.signature,
            'signed_by': self.signed_by,
            # On garde la date d'une signature déjà donnée en ligne
            'signed_on': (intervention.signed_on if self.signature == intervention.customer_signature
                          else fields.Datetime.now()) or fields.Datetime.now(),
            'part_ids': [Command.create({
                'product_id': line.product_id.id,
                'quantity': line.quantity,
            }) for line in self.line_ids],
        })
        # Sortie de stock standard des pièces, puis passage à « Terminée »
        intervention._techserv_create_parts_picking()
        intervention.write({'stage_id': intervention._get_techserv_stage('done').id})
        return {'type': 'ir.actions.act_window_close'}


class TechservInterventionCloseWizardLine(models.TransientModel):
    _name = 'techserv.intervention.close.wizard.line'
    _description = 'Close an Intervention - Part Line'

    wizard_id = fields.Many2one('techserv.intervention.close.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, domain="[('type', '=', 'consu')]")
    quantity = fields.Float(string='Quantity', digits='Product Unit', default=1.0, required=True)
