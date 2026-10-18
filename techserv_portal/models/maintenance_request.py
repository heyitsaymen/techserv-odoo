from odoo import models


class MaintenanceRequest(models.Model):
    """On ajoute le mixin standard ``portal.mixin`` à l'intervention : il apporte
    l'URL portail (access_url), le jeton de partage (access_token) et les
    méthodes utilisées par les contrôleurs et templates du portail."""
    _name = 'maintenance.request'
    _inherit = ['maintenance.request', 'portal.mixin']

    def _compute_access_url(self):
        super()._compute_access_url()
        for request in self:
            request.access_url = f'/my/interventions/{request.id}'

    def _get_report_base_filename(self):
        # Nom du PDF téléchargé depuis le portail
        self.ensure_one()
        return f"Intervention Report - {self.reference}"

    def _techserv_portal_can_sign(self):
        """Le client peut signer en ligne une intervention planifiée ou en cours,
        pas encore signée. La signature est ensuite reprise par l'assistant de
        clôture du technicien (qui reste obligatoire pour clôturer)."""
        self.ensure_one()
        return self.techserv_state in ('planned', 'in_progress') and not self.customer_signature
