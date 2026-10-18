from . import models


def post_init_hook(env):
    """Donne une référence aux demandes de maintenance qui existaient avant
    l'installation du module (sinon elles resteraient sans référence)."""
    requests = env['maintenance.request'].with_context(active_test=False).search(
        [('reference', '=', False)], order='id')
    for request in requests:
        request.reference = env['ir.sequence'].next_by_code('techserv.intervention')
