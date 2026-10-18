from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestEquipment(TechservCommon):

    def test_serial_number_unique(self):
        """Deux équipements ne peuvent pas avoir le même numéro de série (contrainte SQL)."""
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.Equipment.create({'name': 'Duplicate', 'serial_no': 'TS-TEST-0001'})
            self.env.flush_all()

    def test_under_warranty_search(self):
        """Le champ calculé non stocké est cherchable grâce à sa méthode search=."""
        no_date = self.Equipment.create({'name': 'No warranty date', 'customer_id': self.customer.id})
        ours = self.equipment_warranty | self.equipment_expired | no_date
        under = self.Equipment.search([('is_under_warranty', '=', True), ('id', 'in', ours.ids)])
        not_under = self.Equipment.search([('is_under_warranty', '=', False), ('id', 'in', ours.ids)])
        self.assertEqual(under, self.equipment_warranty)
        self.assertEqual(not_under, self.equipment_expired | no_date)
        self.assertTrue(self.equipment_warranty.is_under_warranty)
        self.assertFalse(self.equipment_expired.is_under_warranty)

    def test_warranty_at_date(self):
        """La garantie s'apprécie à une date donnée (utile pour la facturation)."""
        expired = self.equipment_expired
        self.assertTrue(expired._is_under_warranty_at(expired.warranty_date - timedelta(days=1)))
        self.assertTrue(expired._is_under_warranty_at(expired.warranty_date))
        self.assertFalse(expired._is_under_warranty_at(fields.Date.today()))

    def test_new_intervention_button(self):
        """Le bouton « Nouvelle intervention » pré-remplit client et équipement."""
        action = self.equipment_warranty.action_new_intervention()
        intervention = self.Intervention.with_context(action['context']).create({'name': 'From equipment'})
        self.assertEqual(intervention.equipment_id, self.equipment_warranty)
        self.assertEqual(intervention.customer_id, self.customer)

    def test_customer_filter_and_counters(self):
        """Filtre « A des équipements » et compteurs sur le contact."""
        partners = self.env['res.partner'].search([
            ('equipment_ids', '!=', False), ('id', 'in', (self.customer | self.customer_b).ids)])
        self.assertEqual(partners, self.customer)
        self._create_intervention()
        self.assertEqual(self.customer.equipment_count, 2)
        self.assertEqual(self.customer.intervention_count, 1)
        self.assertEqual(self.customer_b.equipment_count, 0)
