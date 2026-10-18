from odoo import fields, models


class HrEmployee(models.Model):
    """Technicien = employé standard lié à un utilisateur.

    Rien n'est dupliqué : adresse et téléphones sont ceux de l'employé (et de son
    contact de travail ``work_contact_id``), le coût horaire vient du module
    standard ``hr_hourly_cost``, le véhicule de ``hr_fleet`` (conducteur du
    véhicule) et les certifications de ``hr_skills`` (types de compétence
    « certification » avec dates de validité). On ajoute seulement un compteur.
    """
    _inherit = 'hr.employee'

    intervention_count = fields.Integer(
        string='Interventions', compute='_compute_intervention_count', groups='hr.group_hr_user')

    def _compute_intervention_count(self):
        data = self.env['maintenance.request']._read_group(
            [('user_id', 'in', self.user_id.ids)], ['user_id'], ['__count'])
        count_by_user = {user.id: count for user, count in data}
        for employee in self:
            employee.intervention_count = count_by_user.get(employee.user_id.id, 0)

    def action_view_interventions(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
        action['domain'] = [('user_id', '=', self.user_id.id)]
        action['context'] = {'default_user_id': self.user_id.id}
        return action
