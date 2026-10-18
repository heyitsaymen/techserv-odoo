from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class TechservInterventionPlanWizard(models.TransientModel):
    """Attribution groupée : la planificatrice sélectionne des demandes dans la
    liste (menu Action) et les donne à un technicien à partir d'une heure de
    départ ; les créneaux s'enchaînent selon la durée de chaque intervention."""
    _name = 'techserv.intervention.plan.wizard'
    _description = 'Assign Interventions to a Technician'

    def _default_intervention_ids(self):
        return self.env['maintenance.request'].browse(self.env.context.get('active_ids', []))

    def _default_start_datetime(self):
        # Prochaine heure pleine
        now = fields.Datetime.now()
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    intervention_ids = fields.Many2many(
        'maintenance.request', string='Interventions', default=_default_intervention_ids, required=True)
    user_id = fields.Many2one(
        'res.users', string='Technician', required=True,
        domain=lambda self: [
            ('share', '=', False),
            ('all_group_ids', 'in', self.env.ref('techserv_intervention.group_techserv_technician').ids),
        ])
    start_datetime = fields.Datetime(string='Start', required=True, default=_default_start_datetime)
    default_duration = fields.Float(
        string='Default Duration', default=1.0, required=True,
        help="Duration (in hours) used for interventions that have no duration yet.")

    @api.constrains('default_duration')
    def _check_default_duration(self):
        if any(wizard.default_duration <= 0 for wizard in self):
            raise ValidationError(self.env._("The default duration must be positive."))

    def action_plan(self):
        self.ensure_one()
        interventions = self.intervention_ids
        interventions._check_techserv_manager(self.env._("Only TechServ managers can plan interventions."))
        wrong = interventions.filtered(lambda r: r.techserv_state not in ('received', 'planned'))
        if wrong:
            raise UserError(self.env._(
                "Only received or planned interventions can be assigned: %s",
                ", ".join(wrong.mapped('display_name'))))

        planned_stage = interventions._get_techserv_stage('planned')
        start = self.start_datetime
        # Les plus urgentes d'abord, puis les plus anciennes
        for intervention in interventions.sorted(lambda r: (-int(r.priority or 0), r.id)):
            end = start + timedelta(hours=intervention.duration or self.default_duration)
            # write() standard : planifier user_id + schedule_date crée déjà une activité
            # pour le technicien et l'abonne à l'intervention (activity_update / _add_followers).
            # La contrainte de chevauchement est vérifiée à chaque écriture.
            intervention.write({
                'user_id': self.user_id.id,
                'schedule_date': start,
                'schedule_end': end,
                'stage_id': planned_stage.id,
            })
            start = end
        return {'type': 'ir.actions.act_window_close'}
