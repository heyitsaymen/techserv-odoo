from datetime import timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestPlanWizard(TechservCommon):

    def _plan_wizard(self, interventions, user, hour, **values):
        wizard = self.env['techserv.intervention.plan.wizard'].with_user(self.manager).with_context(
            active_model='maintenance.request', active_ids=interventions.ids,
        ).create({'user_id': user.id, 'start_datetime': self.day + timedelta(hours=hour), **values})
        return wizard.action_plan()

    def test_bulk_assignment(self):
        """Attribution groupée : créneaux enchaînés, étape Planifiée, technicien prévenu."""
        low = self._create_intervention(priority='1')
        urgent = self._create_intervention(priority='3')
        normal = self._create_intervention(priority='2')
        self._plan_wizard(low | urgent | normal, self.tech1, hour=8, default_duration=2)

        self.assertEqual(set((low | urgent | normal).mapped('techserv_state')), {'planned'})
        self.assertEqual((low | urgent | normal).user_id, self.tech1)
        # Les plus urgentes d'abord, sans trou ni chevauchement
        self.assertEqual(urgent.schedule_date, self.day + timedelta(hours=8))
        self.assertEqual(normal.schedule_date, urgent.schedule_end)
        self.assertEqual(low.schedule_date, normal.schedule_end)
        self.assertEqual(low.schedule_end, self.day + timedelta(hours=14))
        # Notification du technicien : activité standard de maintenance
        activity_type = self.env.ref('maintenance.mail_act_maintenance_request')
        for intervention in low | urgent | normal:
            activity = intervention.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
            self.assertEqual(activity.user_id, self.tech1)

    def test_bulk_assignment_respects_overlap(self):
        self._plan(self._create_intervention(), self.tech1, hour=9)
        with self.assertRaises(ValidationError):
            self._plan_wizard(self._create_intervention() | self._create_intervention(), self.tech1, hour=8)


@tagged('post_install', '-at_install')
class TestCloseWizard(TechservCommon):

    def test_close_without_signature(self):
        """Clôture impossible sans la signature du client."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        with self.assertRaises(UserError):
            self._close(intervention, signature=False, user=self.tech1)
        self.assertEqual(intervention.techserv_state, 'planned')
        # Ni en forçant l'étape « Terminée » directement
        with self.assertRaises(UserError):
            intervention.write({'stage_id': self.stage_done.id})

    def test_close_creates_stock_exit(self):
        """À la clôture, les pièces sortent du stock (bon de sortie validé)."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        # Le technicien n'a aucun droit Inventaire : la sortie de stock doit quand même se faire
        self.assertFalse(self.tech1.has_group('stock.group_stock_user'))
        self._close(intervention, parts=[(self.part_filter, 2)], time_spent=2, user=self.tech1)

        self.assertEqual(intervention.techserv_state, 'done')
        self.assertEqual(intervention.time_spent, 2)
        self.assertTrue(intervention.customer_signature)
        self.assertTrue(intervention.signed_on)
        picking = intervention.picking_id
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.picking_type_id, self.warehouse.out_type_id)
        self.assertEqual(picking.move_ids.product_id, self.part_filter)
        self.assertEqual(picking.move_ids.quantity, 2)
        self.assertEqual(intervention.part_ids.move_id, picking.move_ids)
        self.assertEqual(self.part_filter.with_context(warehouse_id=self.warehouse.id).qty_available, 8)

    def test_close_without_parts(self):
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        self._close(intervention, user=self.tech1)
        self.assertEqual(intervention.techserv_state, 'done')
        self.assertFalse(intervention.picking_id)


@tagged('post_install', '-at_install')
class TestInvoiceWizard(TechservCommon):

    def _done_intervention(self, equipment, hour, parts=(), time_spent=2):
        intervention = self._plan(self._create_intervention(equipment_id=equipment.id), self.tech1, hour=hour)
        return self._close(intervention, parts=parts, time_spent=time_spent)

    def _invoice(self, interventions, grouping='customer'):
        wizard = self.env['techserv.intervention.invoice.wizard'].with_user(self.manager).with_context(
            active_model='maintenance.request', active_ids=interventions.ids,
        ).create({'grouping': grouping})
        wizard.action_create_invoices()
        return interventions.invoice_id

    def test_invoice_under_warranty(self):
        """Sous garantie : pas de main-d'oeuvre, mais les pièces sont facturées."""
        intervention = self._done_intervention(self.equipment_warranty, 9, parts=[(self.part_filter, 1)])
        invoice = self._invoice(intervention)
        product_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
        self.assertNotIn(self.labour, product_lines.product_id)
        self.assertEqual(product_lines.product_id, self.part_filter)
        self.assertEqual(product_lines.quantity, 1)
        self.assertEqual(intervention.techserv_state, 'invoiced')

    def test_invoice_out_of_warranty(self):
        """Hors garantie : main-d'oeuvre (quantité = temps passé) et pièces facturées."""
        intervention = self._done_intervention(
            self.equipment_expired, 9, parts=[(self.part_filter, 3)], time_spent=2.5)
        invoice = self._invoice(intervention)
        labour_line = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.labour)
        part_line = invoice.invoice_line_ids.filtered(lambda l: l.product_id == self.part_filter)
        self.assertEqual(labour_line.quantity, 2.5)
        self.assertEqual(labour_line.price_unit, self.labour.lst_price)
        self.assertEqual(part_line.quantity, 3)
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.move_type, 'out_invoice')

    def test_warranty_checked_at_intervention_date(self):
        """La garantie est évaluée à la date de l'intervention, pas à la date de facturation."""
        intervention = self._done_intervention(self.equipment_expired, 9)
        intervention.close_date = self.equipment_expired.warranty_date - timedelta(days=5)
        invoice = self._invoice(intervention)
        self.assertNotIn(self.labour, invoice.invoice_line_ids.product_id)

    def test_grouping(self):
        """Une facture par client, ou une facture par intervention."""
        first = self._done_intervention(self.equipment_expired, 9)
        second = self._done_intervention(self.equipment_expired, 11)
        invoice = self._invoice(first | second, grouping='customer')
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.intervention_ids, first | second)
        self.assertIn(first.reference, invoice.invoice_origin)

        third = self._done_intervention(self.equipment_expired, 13)
        fourth = self._done_intervention(self.equipment_expired, 15)
        invoices = self._invoice(third | fourth, grouping='intervention')
        self.assertEqual(len(invoices), 2)

    def test_only_done_interventions(self):
        planned = self._plan(self._create_intervention(), self.tech1, hour=9)
        with self.assertRaises(UserError):
            self._invoice(planned)
