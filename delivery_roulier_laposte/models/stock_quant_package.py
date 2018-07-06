# coding: utf-8
#  @author Raphael Reverdy <raphael.reverdy@akretion.com>
#          David BEAL <david.beal@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging
from odoo import _, api, models

_logger = logging.getLogger(__name__)
try:
    from roulier.carriers.laposte.laposte_transport import LaposteTransport
    LAPOSTE_WS = LaposteTransport.LAPOSTE_WS
except ImportError as err:
    _logger.debug(err)


CUSTOMS_MAP = {
    'gift': 1,
    'sample': 2,
    'commercial': 3,
    'document': 4,
    'other': 5,
    'return': 6,
}

PICKUP_CARRIER_CODES = ['A2P', 'BPR', 'ACP', 'CDI', 'CMT', 'BDP', 'PCS']


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    def _laposte_before_call(self, picking, request):
        def calc_package_price():
            return sum(
                [op.product_id.list_price * op.product_qty
                    for op in self.get_operations()]
            )
        # TODO _get_options is called fo each package by the result
        # is the same. Should be store after first call
        request['parcels'][0].update(picking._laposte_get_options(self))
        if request['parcels'][0].get('COD'):
            request['parcels'][0]['codAmount'] = self._get_cash_on_delivery(
                picking)
        request['service']['totalAmount'] = '%.f' % (  # truncate to string
            calc_package_price() * 100  # totalAmount is in centimes
        )
        request['service']['returnTypeChoice'] = 3  # do not return to sender
        if picking.carrier_code in PICKUP_CARRIER_CODES:
            request['parcels'][0]['pickupLocationId'] = \
                self._laposte_dropoff_site(picking)
        return request

    @api.multi
    def _laposte_dropoff_site(self, picking):
        return picking.partner_id.dropoff_site_number

    @api.multi
    def _laposte_get_customs(self, picking):
        """ see _roulier_get_customs() docstring
        """
        customs = self._roulier_get_customs(picking)
        customs['category'] = CUSTOMS_MAP.get(picking.customs_category)
        return customs

    @api.multi
    def _laposte_should_include_customs(self, picking):
        """Choose if customs infos should be included in the WS call.

        Return bool
        """
        # Customs declaration (cn23) is needed when :
        # dest is not in UE
        # dest is attached territory (like Groenland, Canaries)
        # dest is is Outre-mer
        #
        # If origin is not France metropole, this implementation may be wrong.
        # see https://boutique.laposte.fr/_ui/doc/formalites_douane.pdf
        sender_is_intrastat = picking._get_sender(self).country_id.intrastat
        receiver_is_intrastat = (
            picking._get_receiver(self).country_id.intrastat)
        if sender_is_intrastat:
            if receiver_is_intrastat:
                return False  # national or within UE
            else:
                return True  # internationnal shipping
        else:
            _logger.warning(
                'Customs may be not needed for picking %s'
                % picking.id)
            return True

    @api.model
    def _laposte_invalid_api_input_handling(self, payload, exception):
        payload['auth']['password'] = '****'
        response = exception.message
        # on met des clés plus explicites vis à vis des objets odoo
        suffix = (
            u"\nSignification des clés dans le contexte Odoo:\n"
            u"- 'to_address' : adresse du destinataire (votre client)\n"
            u"- 'from_address' : adresse de l'expéditeur (vous)")
        message = u'Données transmises:\n%s\n\nExceptions levées%s\n%s' % (
            payload, response, suffix)
        return message

    def _laposte_carrier_error_handling(self, payload, exception):
        response = exception.response
        request = response.request.body

        if self._uid > 1:
            # rm pwd from dict and xml
            payload['auth']['password'] = '****'
            request = '%s<password>****%s' % (
                request[:request.index('<password>')],
                request[request.index('</password>'):]
            )

        # Webservice error
        # on contextualise les réponses ws aux objets Odoo
        map_responses = {
            30204:
                u"La 2eme ligne d'adresse du client partenaire "
                u"est vide ou invalide",
            30221:
                u"Le telephone du client ne doit comporter que des "
                u"chiffres ou le symbole +: convertissez tous vos N° de "
                u"telephone au format standard a partir du menu suivant:\n"
                u"Configuration > Technique > Telephonie > Reformate "
                u"les numeros de telephone ",
            30100:
                u"La seconde ligne d'adresse de l'expéditeur est "
                u"vide ou invalide.",
        }

        def format_one_exception(message, map_responses):
            param_message = {
                'ws_exception':
                    u'%s\n' % message['message'],
                'resolution': u''}
            if message and message.get('id') in map_responses.keys():
                param_message['resolution'] = _(
                    u"Résolution\n-------------\n%s" %
                    map_responses[message['id']]
                )
            return _(u"Réponse de Laposte:\n"
                     u"%(ws_exception)s\n%(resolution)s"
                     % param_message)

        parts = []
        for messages in exception:
            for message in messages:
                parts.append(format_one_exception(message, map_responses))

        ret_mess = _(u"Incident\n-----------\n%s\n"
                     u"Données transmises:\n"
                     u"-----------------------------\n%s\n\nWS: %s") % (
            u'\n'.join(parts), request.decode('utf-8'), LAPOSTE_WS)
        return ret_mess

    def _laposte_get_tracking_link(self):
        return (
            "https://www.colissimo.fr/"
            "portail_colissimo/suivreResultat.do?"
            "parcelnumber=%s" % self.parcel_tracking)
