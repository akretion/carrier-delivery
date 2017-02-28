# coding: utf-8
#  @author Raphael Reverdy @ Akretion <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from openerp import models
from openerp.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _roulier_get_account(self, package):
        """Returns an 'account'.

        We return an account based on the delivery method's technical name"""
        self.ensure_one()
        keychain = self.env['keychain.account']
        if self.env.user.has_group('stock.group_stock_user'):
            retrieve = keychain.suspend_security().retrieve
        else:
            retrieve = keychain.retrieve

        technical_name = self.carrier_id.keychain_account.technical_name
        accounts = retrieve(
            [
                ['namespace', '=', 'roulier_%s' % self.carrier_type],
                ['technical_name', '=', technical_name]
            ])
        if len(accounts) == 0:
            _logger.debug('Searching an account for %s' % technical_name)
            raise UserError("No account found based on the delivery_method")

        return accounts[0]