from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestAlerts(TechservCommon):

    def _age(self, interventions, hours):
        """Simule l'ancienneté d'une demande en reculant sa date de création."""
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE maintenance_request SET create_date = %s WHERE id IN %s",
            (fields.Datetime.now() - timedelta(hours=hours), tuple(interventions.ids)))
        self.env.invalidate_all()

    def test_urgent_not_planned_after_24h(self):
        """Alerte au responsable pour une urgence non planifiée après 24 h, sans doublon."""
        automation = self.env.ref('techserv_intervention.automation_urgent_unplanned')
        alert_type = self.env.ref('techserv_intervention.mail_activity_type_urgent_unplanned')
        urgent = self._create_intervention(priority='3')
        normal = self._create_intervention(priority='1')
        urgent_planned = self._plan(self._create_intervention(priority='3'), self.tech1, hour=9)
        urgent_recent = self._create_intervention(priority='3')
        self._age(urgent | normal | urgent_planned, hours=25)
        self._age(urgent_recent, hours=2)

        # Même recherche et même exécution que la tâche planifiée du moteur base_automation
        records = automation._search_time_based_automation_records(until=fields.Datetime.now())
        self.assertIn(urgent, records)
        self.assertNotIn(normal, records)
        self.assertNotIn(urgent_planned, records)
        self.assertNotIn(urgent_recent, records)
        automation._process(records)

        alerts = urgent.activity_ids.filtered(lambda a: a.activity_type_id == alert_type)
        self.assertIn(self.manager, alerts.user_id)
        self.assertEqual(alerts.user_id, urgent._techserv_get_managers())
        # Seconde exécution : pas de doublon
        automation._process(records)
        self.assertEqual(urgent.activity_ids.filtered(lambda a: a.activity_type_id == alert_type), alerts)

    def test_email_customer_when_planned(self):
        """Le client reçoit un e-mail dès que l'intervention passe à « Planifiée »."""
        intervention = self._create_intervention()
        Mail = self.env['mail.mail']
        domain = [
            ('model', '=', 'maintenance.request'), ('res_id', '=', intervention.id),
            ('recipient_ids', 'in', self.customer.id),
        ]
        self.assertFalse(Mail.search(domain))
        self._plan(intervention, self.tech1, hour=9)
        mail = Mail.search(domain)
        self.assertEqual(len(mail), 1)
        self.assertIn(intervention.reference, mail.subject)
        # Pas de second e-mail si l'intervention reste planifiée (changement de date)
        intervention.schedule_date = self.day + timedelta(hours=14)
        self.assertEqual(len(Mail.search(domain)), 1)
