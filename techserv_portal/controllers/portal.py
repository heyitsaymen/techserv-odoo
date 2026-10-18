import binascii

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class TechservCustomerPortal(CustomerPortal):
    """Pages « Mes interventions » du portail client (héritage du contrôleur standard)."""

    def _prepare_home_portal_values(self, counters):
        # Compteur affiché sur la page d'accueil du portail (/my)
        values = super()._prepare_home_portal_values(counters)
        if 'intervention_count' in counters:
            Intervention = request.env['maintenance.request']
            values['intervention_count'] = Intervention.search_count(
                self._prepare_interventions_domain(request.env.user.partner_id)
            ) if Intervention.has_access('read') else 0
        return values

    def _prepare_interventions_domain(self, partner):
        return [('customer_id', 'child_of', [partner.commercial_partner_id.id])]

    @http.route(['/my/interventions', '/my/interventions/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_interventions(self, page=1, sortby='date', **kw):
        Intervention = request.env['maintenance.request']
        domain = self._prepare_interventions_domain(request.env.user.partner_id)
        searchbar_sortings = {
            'date': {'label': _("Newest"), 'order': 'request_date desc, id desc'},
            'reference': {'label': _("Reference"), 'order': 'reference desc'},
            'stage': {'label': _("Stage"), 'order': 'stage_id, id desc'},
        }
        sortby = sortby if sortby in searchbar_sortings else 'date'
        # La recherche se fait avec les droits du client (règle portail), l'affichage en sudo
        can_read = Intervention.has_access('read')
        pager = portal_pager(
            url='/my/interventions',
            url_args={'sortby': sortby},
            total=Intervention.search_count(domain) if can_read else 0,
            page=page,
            step=self._items_per_page,
        )
        interventions = Intervention.search(
            domain, order=searchbar_sortings[sortby]['order'],
            limit=self._items_per_page, offset=pager['offset'],
        ) if can_read else Intervention
        request.session['my_interventions_history'] = interventions.ids[:100]

        values = self._prepare_portal_layout_values()
        values.update({
            'interventions': interventions.sudo(),
            'page_name': 'intervention',
            'pager': pager,
            'default_url': '/my/interventions',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render('techserv_portal.portal_my_interventions', values)

    # website=True (comme le portail standard) : prépare le layout frontend (langues...),
    # même sans le module Website installé
    @http.route(['/my/interventions/<int:intervention_id>'], type='http', auth='public', website=True)
    def portal_my_intervention(self, intervention_id, access_token=None, report_type=None,
                               download=False, message=False, **kw):
        try:
            # Vérifie les droits du client OU le jeton de partage (lien envoyé par e-mail)
            intervention_sudo = self._document_check_access(
                'maintenance.request', intervention_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(
                model=intervention_sudo, report_type=report_type,
                report_ref='techserv_intervention.action_report_intervention', download=download)

        values = {
            'intervention': intervention_sudo,
            'page_name': 'intervention',
            'message': message,
            'report_type': 'html',
            'res_company': intervention_sudo.company_id,
        }
        values = self._get_page_view_values(
            intervention_sudo, access_token, values, 'my_interventions_history', False, **kw)
        return request.render('techserv_portal.portal_my_intervention', values)

    @http.route(['/my/interventions/<int:intervention_id>/sign'], type='jsonrpc', auth='public', website=True)
    def portal_intervention_sign(self, intervention_id, access_token=None, name=None, signature=None):
        """Appelée par le composant standard portal.signature_form (même principe que
        la signature des devis dans le module sale)."""
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            intervention_sudo = self._document_check_access(
                'maintenance.request', intervention_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _("Invalid intervention.")}

        if not intervention_sudo._techserv_portal_can_sign():
            return {'error': _("This intervention cannot be signed.")}
        if not signature:
            return {'error': _("Signature is missing.")}

        try:
            intervention_sudo.write({
                'customer_signature': signature,
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
            })
            request.env.cr.flush()
        except (TypeError, binascii.Error):
            return {'error': _("Invalid signature data.")}

        intervention_sudo.message_post(
            body=_("Intervention report signed online by %s.", name),
            author_id=(intervention_sudo.customer_id.id if request.env.user._is_public()
                       else request.env.user.partner_id.id),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'force_refresh': True,
            'redirect_url': intervention_sudo.get_portal_url(query_string='&message=sign_ok'),
        }
