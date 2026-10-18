from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.techserv_intervention.tests.common import SIGNATURE, TechservCommon


@tagged('post_install', '-at_install')
class TestPortal(TechservCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Utilisateur portail rattaché au client A (new_test_user : mot de passe = login)
        cls.portal_user = new_test_user(
            cls.env, login='ts_portal', groups='base.group_portal', partner_id=cls.customer.id)
        equipment_b = cls.Equipment.create({'name': 'AC B', 'customer_id': cls.customer_b.id})
        cls.mine = cls._create_intervention(name='Portal mine')
        cls.other = cls._create_intervention(name='Portal other', equipment_id=equipment_b.id)

    def test_portal_user_sees_only_his_interventions(self):
        Intervention = self.Intervention.with_user(self.portal_user)
        visible = Intervention.search([('id', 'in', (self.mine | self.other).ids)])
        self.assertEqual(visible, self.mine)
        self.assertEqual(self.mine.access_url, f'/my/interventions/{self.mine.id}')

    def test_portal_pages(self):
        self.authenticate('ts_portal', 'ts_portal')
        response = self.url_open('/my/interventions')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine.reference, response.text)
        self.assertNotIn(self.other.reference, response.text)

        response = self.url_open(self.mine.access_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine.reference, response.text)
        # La fiche d'un autre client renvoie vers l'accueil du portail
        response = self.url_open(self.other.access_url)
        self.assertTrue(response.url.endswith('/my'))
        # Bon d'intervention (version HTML du rapport PDF)
        response = self.url_open(f'{self.mine.access_url}?report_type=html')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mine.reference, response.text)

    def test_portal_home_counter(self):
        self.authenticate('ts_portal', 'ts_portal')
        counters = self.make_jsonrpc_request('/my/counters', {'counters': ['intervention_count']})
        self.assertEqual(counters['intervention_count'], 1)

    def test_sign_online_then_close(self):
        """Le client signe en ligne ; le technicien clôture ensuite avec cette signature."""
        self._plan(self.mine, self.tech1, hour=9)
        self.assertTrue(self.mine._techserv_portal_can_sign())
        self.authenticate('ts_portal', 'ts_portal')
        result = self.make_jsonrpc_request(
            f'{self.mine.access_url}/sign', {'name': 'Customer A', 'signature': SIGNATURE.decode()})
        self.assertTrue(result.get('force_refresh'), result)
        self.env.invalidate_all()  # la requête HTTP a modifié l'enregistrement
        self.assertTrue(self.mine.customer_signature)
        self.assertEqual(self.mine.signed_by, 'Customer A')
        self.assertFalse(self.mine._techserv_portal_can_sign())

        # Second envoi refusé : déjà signé
        result = self.make_jsonrpc_request(
            f'{self.mine.access_url}/sign', {'name': 'Customer A', 'signature': SIGNATURE.decode()})
        self.assertIn('error', result)

        # La clôture reprend la signature du portail (aucune signature saisie dans l'assistant)
        wizard = self.env['techserv.intervention.close.wizard'].with_user(self.tech1).with_context(
            active_model='maintenance.request', active_id=self.mine.id).create({'time_spent': 1})
        wizard.action_close()
        self.assertEqual(self.mine.techserv_state, 'done')
        self.assertEqual(self.mine.signed_by, 'Customer A')

    def test_cannot_sign_other_customer_intervention(self):
        self._plan(self.other, self.tech1, hour=9)
        self.authenticate('ts_portal', 'ts_portal')
        result = self.make_jsonrpc_request(
            f'{self.other.access_url}/sign', {'name': 'Intruder', 'signature': SIGNATURE.decode()})
        self.assertIn('error', result)
        self.env.invalidate_all()
        self.assertFalse(self.other.customer_signature)
