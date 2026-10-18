from odoo.tests import tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestReports(TechservCommon):

    def test_intervention_report(self):
        """Le bon d'intervention se génère avec la référence, les pièces et la signature."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        self._close(intervention, parts=[(self.part_filter, 1)])
        html = str(self.env['ir.actions.report']._render_qweb_html(
            'techserv_intervention.action_report_intervention', intervention.ids)[0])
        self.assertIn(intervention.reference, html)
        self.assertIn(self.part_filter.name, html)
        self.assertIn('data:image/png;base64', html)

    def test_invoice_report_shows_reference_and_serial(self):
        """La facture imprimée affiche la référence d'intervention et le n° de série."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        self._close(intervention)
        invoice = intervention._techserv_create_invoices()
        invoice.action_post()
        html = str(self.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids)[0])
        self.assertIn(intervention.reference, html)
        self.assertIn(self.equipment_expired.serial_no, html)
