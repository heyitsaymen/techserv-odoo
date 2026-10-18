from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestSecurity(TechservCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mine = cls._create_intervention(name='Mine')
        cls.other = cls._create_intervention(name='Other technician')
        cls.unassigned = cls._create_intervention(name='Unassigned')

    def setUp(self):
        super().setUp()
        self._plan(self.mine, self.tech1, hour=9)
        self._plan(self.other, self.tech2, hour=9)
        self.ours = self.mine | self.other | self.unassigned

    def test_technician_sees_only_his_interventions(self):
        """Isolement des données : le technicien ne voit que ses interventions."""
        visible = self.Intervention.with_user(self.tech1).search([('id', 'in', self.ours.ids)])
        self.assertEqual(visible, self.mine)
        with self.assertRaises(AccessError):
            self.other.with_user(self.tech1).read(['name'])
        with self.assertRaises(AccessError):
            self.other.with_user(self.tech1).write({'name': 'Hacked'})
        # Il peut lire l'équipement client et travailler sur sa propre intervention
        self.assertTrue(self.mine.with_user(self.tech1).equipment_id.serial_no)
        self.mine.with_user(self.tech1).action_techserv_start()
        self.assertEqual(self.mine.techserv_state, 'in_progress')

    def test_manager_sees_everything(self):
        visible = self.Intervention.with_user(self.manager).search([('id', 'in', self.ours.ids)])
        self.assertEqual(visible, self.ours)

    def test_technician_cannot_cancel_delete_or_invoice(self):
        """Contrôles côté serveur, indépendants des boutons affichés."""
        mine = self.mine.with_user(self.tech1)
        with self.assertRaises(AccessError):
            mine.action_techserv_cancel()
        with self.assertRaises(AccessError):
            mine.write({'stage_id': self.stage_cancel.id})
        with self.assertRaises(AccessError):
            mine.unlink()
        self._close(self.mine, user=self.tech1)
        with self.assertRaises(AccessError):
            self.mine.with_user(self.tech1)._techserv_create_invoices()
        # L'assistant de facturation n'est même pas accessible (droits d'accès)
        with self.assertRaises(AccessError):
            self.env['techserv.intervention.invoice.wizard'].with_user(self.tech1).create({})
        # L'assistant de planification non plus
        with self.assertRaises(AccessError):
            self.env['techserv.intervention.plan.wizard'].with_user(self.tech1).create({
                'user_id': self.tech1.id, 'intervention_ids': [(6, 0, self.mine.ids)]})

    def test_multi_company(self):
        """Chaque société ne voit que ses propres interventions et équipements."""
        company_b = self.env['res.company'].create({'name': 'TechServ B'})
        team_b = self.env['maintenance.team'].create({'name': 'Team B', 'company_id': company_b.id})
        equipment_b = self.Equipment.create({
            'name': 'AC B', 'customer_id': self.customer_b.id, 'company_id': company_b.id, 'serial_no': 'TS-B-1'})
        intervention_b = self.Intervention.create({
            'name': 'Company B', 'equipment_id': equipment_b.id, 'company_id': company_b.id,
            'maintenance_team_id': team_b.id})
        manager_a = new_test_user(
            self.env, login='ts_manager_a', groups='techserv_intervention.group_techserv_manager',
            company_id=self.company.id, company_ids=[(6, 0, self.company.ids)])
        Intervention = self.Intervention.with_user(manager_a)
        self.assertFalse(Intervention.search([('id', '=', intervention_b.id)]))
        self.assertFalse(self.Equipment.with_user(manager_a).search([('id', '=', equipment_b.id)]))
        self.assertTrue(Intervention.search([('id', '=', self.mine.id)]))
        self.assertEqual(intervention_b.reference[:4], 'INT/')
