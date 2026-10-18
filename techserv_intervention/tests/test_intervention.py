from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from .common import TechservCommon


@tagged('post_install', '-at_install')
class TestIntervention(TechservCommon):

    def test_reference_sequence(self):
        """Chaque intervention reçoit une référence unique, utilisable en recherche."""
        first = self._create_intervention()
        second = self._create_intervention()
        self.assertTrue(first.reference.startswith('INT/'))
        self.assertNotEqual(first.reference, second.reference)
        self.assertIn(first.reference, first.display_name)
        self.assertEqual(self.Intervention.search([('display_name', 'ilike', first.reference)]), first)
        self.assertEqual(first.customer_id, self.customer, "Customer taken from the equipment")

    def test_technician_overlap(self):
        """Un technicien ne peut pas avoir deux interventions qui se chevauchent."""
        first = self._plan(self._create_intervention(), self.tech1, hour=9, duration=2)
        second = self._create_intervention()
        with self.assertRaises(ValidationError):
            self._plan(second, self.tech1, hour=10)
        # Un autre technicien sur le même créneau : autorisé
        self._plan(second, self.tech2, hour=10)
        # Un créneau qui commence à la fin du précédent : autorisé
        third = self._plan(self._create_intervention(), self.tech1, hour=11)
        self.assertEqual(third.techserv_state, 'planned')
        # Une intervention annulée ne bloque plus le créneau
        first.with_user(self.manager).action_techserv_cancel()
        fourth = self._plan(self._create_intervention(), self.tech1, hour=9)
        self.assertEqual(fourth.user_id, self.tech1)

    def test_planning_requires_technician_and_date(self):
        intervention = self._create_intervention()
        with self.assertRaises(ValidationError):
            intervention.stage_id = self.stage_planned

    def test_cancel_before_start(self):
        """On peut annuler tant que le technicien n'est pas parti."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        intervention.with_user(self.manager).action_techserv_cancel()
        self.assertEqual(intervention.techserv_state, 'cancel')
        self.assertTrue(intervention.archive)

    def test_cancel_forbidden_after_start(self):
        """Annulation impossible une fois l'intervention « En cours » (contrôle serveur)."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        intervention.with_user(self.tech1).action_techserv_start()
        self.assertEqual(intervention.techserv_state, 'in_progress')
        with self.assertRaises(UserError):
            intervention.with_user(self.manager).action_techserv_cancel()
        # Même en contournant le bouton (écriture directe de l'étape, glisser-déposer kanban)
        with self.assertRaises(UserError):
            intervention.with_user(self.manager).write({'stage_id': self.stage_cancel.id})
        self.assertEqual(intervention.techserv_state, 'in_progress')

    def test_delete_forbidden_after_start(self):
        """Suppression interdite une fois l'intervention commencée (@api.ondelete)."""
        intervention = self._plan(self._create_intervention(), self.tech1, hour=9)
        intervention.action_techserv_start()
        with self.assertRaises(UserError):
            intervention.with_user(self.manager).unlink()
        self.assertTrue(intervention.exists())
        # Une demande non commencée peut être supprimée par le responsable
        draft = self._create_intervention()
        draft.with_user(self.manager).unlink()
        self.assertFalse(draft.exists())

    def test_tracking(self):
        """Traçabilité : les changements de technicien et de date sont historisés."""
        # Le suivi est enregistré juste avant le commit (hooks « precommit »), et les
        # modifications faites dans la transaction de création ne sont pas suivies :
        # on simule donc deux transactions successives.
        intervention = self._create_intervention()
        self.env.cr.precommit.run()
        self._plan(intervention, self.tech1, hour=9)
        self.env.flush_all()
        self.env.cr.precommit.run()
        tracked = intervention.message_ids.tracking_value_ids.field_id.mapped('name')
        self.assertIn('user_id', tracked)
        self.assertIn('schedule_date', tracked)
        self.assertIn('stage_id', tracked)
