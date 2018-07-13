# coding: utf-8
#  @author Raphael Reverdy <raphael.reverdy@akretion.com>
#          David BEAL <david.beal@akretion.com>
#          Sébastien BEAU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    laposte_insurance = fields.Selection(
        selection=[
            ('15000', 'Assurance 150 €'), ('30000', 'Assurance 300 €'),
            ('45000', 'Assurance 450 €'), ('60000', 'Assurance 600 €'),
            ('75000', 'Assurance 750 €'), ('90000', 'Assurance 900 €'),
            ('105000', 'Assurance 1050 €'), ('120000', 'Assurance 1200 €'),
            ('135000', 'Assurance 1350 €'), ('150000', 'Assurance 1500 €'),
        ], string=u"Assurance",
        help=u"Paramètre incompatible avec le paramètre Recommandé")
    laposte_recommande = fields.Selection(
        selection=[
            ('R1', 'Recommendation R1'), ('R2', 'Recommendation R2'),
            ('R3', 'Recommendation R3'),
        ], string=u"Recommandé",
        help=u"Paramètre incompatible avec le paramètre Assurance")

    @api.constrains('laposte_recommande', 'laposte_insurance')
    def _laposte_check_insurance(self):
        for rec in self:
            if rec.laposte_recommande and rec.laposte_insurance:
                raise(u"Les paramètres 'recommandé' et 'assurance' "
                      u"sont incompatibles.")
            if rec.laposte_recommande and \
                    rec.partner_id.country_id != self.env.ref('base.fr'):
                message = (u"Le paramètre 'recommandé' est restreint "
                           u"aux destinations France")
                raise UserError(message)

    def _laposte_get_shipping_date(self, package_id):
        """Estimate shipping date."""
        self.ensure_one()

        shipping_date = self.min_date
        if self.date_done:
            shipping_date = self.date_done

        shipping_date = datetime.strptime(
            shipping_date, DEFAULT_SERVER_DATETIME_FORMAT)

        tomorrow = datetime.now() + timedelta(1)
        if shipping_date < tomorrow:
            # don't send in the past
            shipping_date = tomorrow

        return shipping_date.strftime('%Y-%m-%d')

    @api.model
    def _laposte_map_options(self):
        return {
            'NM': 'nonMachinable',
            'FCR': 'ftd',
            'COD': 'cod',
            'INS': 'insuranceValue',
        }

    @api.multi
    def _laposte_get_options(self, package):
        """Define options for the shippment.

        Like insurance, cash on delivery...
        It should be the same for all the packages of
        the shipment.
        """
        # should be extracted from a company wide setting
        # and oversetted in a view form
        self.ensure_one()
        options = self._roulier_get_options(package)
        if 'insuranceValue' in options:
            if self.laposte_recommande:
                options['recommendationLevel'] = self.laposte_recommande
                del options['insuranceValue']
            else:
                options['insuranceValue'] = int(self.laposte_insurance)
        if 'cod' in options:
            options['codAmount'] = 0
        return options

    # helpers
    @api.model
    def _laposte_convert_address(self, partner):
        """Convert a partner to an address for roulier.

        params:
            partner: a res.partner
        return:
            dict
        """
        address = self._roulier_convert_address(partner) or {}
        # get_split_adress from partner_helper module
        streets = partner._get_split_address(3, 38)
        address['street'], address['street2'], address['street3'] = streets
        address['firstName'] = '.'
        if 'partner_firstname' in self.env.registry._init_modules \
                and partner.firstname and partner.lastname:
            address['firstName'] = partner.firstname
            address['name'] = partner.lastname
        return address
