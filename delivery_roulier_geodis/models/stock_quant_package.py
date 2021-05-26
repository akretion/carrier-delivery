# coding: utf-8
#  @author Raphael Reverdy <raphael.reverdy@akretion.com>
#          David BEAL <david.beal@akretion.com>
#          EBII MonsieurB <monsieurb@saaslys.com>
#          Sébastien BEAU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import _, api, models, fields
import logging

_logger = logging.getLogger(__name__)


class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    geodis_shippingid = fields.Char(help="Shipping Id in Geodis terminology")
    geodis_cab = fields.Char(help="Barcode of the label")

    @api.multi
    def _geodis_generate_labels(self, picking):
        packages = self
        response = packages._call_roulier_api(picking)
        packages._handle_tracking(picking, response)
        packages._handle_attachments(picking, response)

    @api.multi
    def _geodis_get_parcels(self, picking):
        return [pack._get_parcel(picking) for pack in self]

    def _geodis_before_call(self, picking, request):
        # TODO _get_options is called fo each package by the result
        # is the same. Should be store after first call
        self._gen_shipping_id()
        account = picking._get_account(self)
        service = account.get_data()
        request['service']['customerId'] = service['customerId']
        request['service']['agencyId'] = service['agencyId']
        request['service']['labelFormat'] = service['labelFormat']
        request['service']['shippingId'] = self.geodis_shippingid
        request['service']['is_test'] = service['isTest']
        return request

    def _geodis_handle_tracking(self, picking, response):
        self.geodis_cab = response['extra']['colis']['cab']
        return self._roulier_handle_tracking(picking, response)

    def _geodis_should_include_customs(self, picking):
        """Customs documents not implemented."""
        return False

    @api.multi
    def _gen_shipping_id(self):
        """Generate a shipping id.

        Shipping id is persisted on the picking and it's
        calculated from a sequence since it should be
        8 char long and unique for at least 1 year
        """
        def gen_id():
            sequence = self.env['ir.sequence'].next_by_code(
                "geodis.nrecep.number")
            # this is prefixed by year_ so we split it befor use
            year, number = sequence.split('_')
            # pad with 0 to build an 8digits number (string)
            return '%08d' % int(number)

        for pack in self:
            pack.geodis_shippingid = (
                pack.geodis_shippingid or gen_id()
            )
        return True

    def _geodis_carrier_error_handling(self, payload, exception):
        pay = payload
        pay['auth']['password'] = '****'
        return _(u'Sent data:\n%s\n\nException raised:\n%s\n' % (
            pay, exception.message))
