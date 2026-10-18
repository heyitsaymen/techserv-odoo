from odoo.tests import new_test_user, tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestSale(TechservCommon):

    def test_confirm_quotation_creates_intervention(self):
        """La confirmation du devis crée l'intervention et prévient l'équipe technique."""
        salesman = new_test_user(self.env, login='ts_salesman', groups='sales_team.group_sale_salesman')
        order = self.env['sale.order'].with_user(salesman).create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {'product_id': self.service_install.id, 'product_uom_qty': 1}),
                (0, 0, {'product_id': self.part_filter.id, 'product_uom_qty': 2}),
            ],
        })
        self.assertFalse(order.intervention_ids)
        order.with_user(salesman).action_confirm()

        # Le flux de vente standard est inchangé
        self.assertEqual(order.state, 'sale')
        # Une intervention pour la ligne « crée une intervention » uniquement
        intervention = order.intervention_ids
        self.assertEqual(len(intervention), 1)
        self.assertEqual(order.intervention_count, 1)
        self.assertEqual(intervention.customer_id, self.customer)
        self.assertEqual(intervention.sale_line_id.product_id, self.service_install)
        self.assertEqual(intervention.techserv_state, 'received')
        # Équipe technique prévenue par une activité
        todo = self.env.ref('mail.mail_activity_data_todo')
        notified = intervention.activity_ids.filtered(lambda a: a.activity_type_id == todo).user_id
        self.assertTrue(notified)
        expected = intervention.maintenance_team_id.member_ids or intervention._techserv_get_managers()
        self.assertEqual(notified, expected)

    def test_no_duplicate_on_reconfirmation(self):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'product_id': self.service_install.id, 'product_uom_qty': 1})],
        })
        order.action_confirm()
        order._action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertEqual(len(order.intervention_ids), 1)
