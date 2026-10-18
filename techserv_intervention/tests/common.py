from datetime import datetime, timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user

# Petite image PNG (1x1 pixel) utilisée comme signature du client
SIGNATURE = (
    b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA'
    b'60e6kgAAAABJRU5ErkJggg=='
)


class TechservCommon(TransactionCase):
    """Données communes à tous les tests TechServ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        # Base de test sans plan comptable : on charge le plan générique standard
        if not cls.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1):
            cls.env['account.chart.template'].try_loading('generic_coa', cls.company, install_demo=False)

        cls.Intervention = cls.env['maintenance.request']
        cls.Equipment = cls.env['maintenance.equipment']
        cls.stage_received = cls.Intervention._get_techserv_stage('received')
        cls.stage_planned = cls.Intervention._get_techserv_stage('planned')
        cls.stage_in_progress = cls.Intervention._get_techserv_stage('in_progress')
        cls.stage_done = cls.Intervention._get_techserv_stage('done')
        cls.stage_cancel = cls.Intervention._get_techserv_stage('cancel')

        cls.manager = new_test_user(
            cls.env, login='ts_manager', name='TechServ Manager', email='manager@techserv.test',
            groups='techserv_intervention.group_techserv_manager')
        cls.tech1 = new_test_user(
            cls.env, login='ts_tech1', name='Technician One', email='tech1@techserv.test',
            groups='techserv_intervention.group_techserv_technician')
        cls.tech2 = new_test_user(
            cls.env, login='ts_tech2', name='Technician Two', email='tech2@techserv.test',
            groups='techserv_intervention.group_techserv_technician')

        cls.customer = cls.env['res.partner'].create({'name': 'Customer A', 'email': 'customer.a@example.com'})
        cls.customer_b = cls.env['res.partner'].create({'name': 'Customer B', 'email': 'customer.b@example.com'})

        Product = cls.env['product.product']
        cls.product_ac = Product.create({'name': 'Air Conditioner', 'type': 'consu'})
        cls.part_filter = Product.create({
            'name': 'Air Filter', 'type': 'consu', 'is_storable': True, 'list_price': 12.0})
        cls.service_install = Product.create({
            'name': 'AC Installation', 'type': 'service', 'list_price': 150.0, 'create_intervention': True})
        cls.labour = cls.env.ref('techserv_intervention.product_labour')

        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.env['stock.quant']._update_available_quantity(cls.part_filter, cls.warehouse.lot_stock_id, 10)

        today = fields.Date.today()
        cls.equipment_warranty = cls.Equipment.create({
            'name': 'AC under warranty', 'customer_id': cls.customer.id, 'product_id': cls.product_ac.id,
            'serial_no': 'TS-TEST-0001', 'warranty_date': today + timedelta(days=365),
        })
        cls.equipment_expired = cls.Equipment.create({
            'name': 'AC warranty expired', 'customer_id': cls.customer.id, 'product_id': cls.product_ac.id,
            'serial_no': 'TS-TEST-0002', 'warranty_date': today - timedelta(days=30),
        })
        # Date fixe dans le futur pour les créneaux planifiés
        cls.day = datetime(2030, 1, 7)

    @classmethod
    def _create_intervention(cls, **values):
        vals = {
            'name': 'Not cooling',
            'equipment_id': cls.equipment_expired.id,
            'stage_id': cls.stage_received.id,
        }
        vals.update(values)
        return cls.Intervention.create(vals)

    def _plan(self, intervention, user, hour, duration=1.0):
        start = self.day + timedelta(hours=hour)
        intervention.write({
            'user_id': user.id,
            'schedule_date': start,
            'schedule_end': start + timedelta(hours=duration),
            'stage_id': self.stage_planned.id,
        })
        return intervention

    def _close(self, intervention, parts=(), time_spent=1.5, signature=SIGNATURE, user=None):
        Wizard = self.env['techserv.intervention.close.wizard']
        if user:
            Wizard = Wizard.with_user(user)
        wizard = Wizard.with_context(active_model='maintenance.request', active_id=intervention.id).create({
            'time_spent': time_spent,
            'signature': signature,
            'line_ids': [(0, 0, {'product_id': product.id, 'quantity': qty}) for product, qty in parts],
        })
        wizard.action_close()
        return intervention
