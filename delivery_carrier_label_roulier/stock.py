# coding: utf-8
#  @author Raphael Reverdy @ Akretion <raphael.reverdy@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from functools import wraps
import logging

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import Warning as UserError

_logger = logging.getLogger(__name__)
try:
    from roulier import roulier
except ImportError:
    _logger.debug('Cannot `import roulier`.')

# if you want to integrate a new carrier with Roulier Library
# start from roulier_template.py and read the doc of
# implemented_by_carrier decorator


def implemented_by_carrier(func):
    """Decorator: call _carrier_prefixed method instead.

    Usage:
        @implemented_by_carrier
        def _do_something()
        def _laposte_do_something()
        def _gls_do_something()

    At runtime, picking._do_something() will try to call
    the carrier spectific method or fallback to generic _do_something

    """
    @wraps(func)
    def wrapper(cls, *args, **kwargs):
        fun_name = func.__name__
        fun = '_%s%s' % (cls.carrier_type, fun_name)
        if not hasattr(cls, fun):
            fun = '_roulier%s' % (fun_name)
            # return func(cls, *args, **kwargs)
        return getattr(cls, fun)(*args, **kwargs)
    return wrapper


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # base_delivery_carrier_label API implementataion

    # @api.multi
    # def generate_default_label(self, package_ids=None):
    # useless method

    @api.multi
    def generate_labels(self, package_ids=None):
        """See base_delivery_carrier_label/stock.py."""
        self.ensure_one()

        if self._is_our():
            return self._roulier_generate_labels(
                package_ids=package_ids)
        _super = super(StockPicking, self)
        return _super.generate_labels(package_ids=package_ids)

    @api.multi
    def generate_shipping_labels(self, package_ids=None):
        """See base_delivery_carrier_label/stock.py."""
        self.ensure_one()

        if self._is_our():
            return self._roulier_generate_shipping_labels(
                package_ids=package_ids)
        _super = super(StockPicking, self)
        return _super.generate_shipping_labels(package_ids=package_ids)

    # end of base_label API implementataion

    # API
    @implemented_by_carrier
    def _before_call(self, package_id, request):
        pass

    @implemented_by_carrier
    def _after_call(self, package_id, response):
        pass

    @implemented_by_carrier
    def _is_our(self):
        """Indicate if the current record is managed by roulier.

        returns:
            True or False
        """
        pass

    @implemented_by_carrier
    def _get_sender(self):
        pass

    @implemented_by_carrier
    def _get_receiver(self):
        pass

    @implemented_by_carrier
    def _get_shipping_date(self, package_id):
        pass

    @implemented_by_carrier
    def _get_options(self, package_id):
        pass

    @implemented_by_carrier
    def _get_customs(self, package_id):
        pass

    @implemented_by_carrier
    def _should_include_customs(self, package_id):
        pass

    @implemented_by_carrier
    def _get_auth(self, account):
        pass

    @implemented_by_carrier
    def _get_service(self, package_id):
        pass

    @implemented_by_carrier
    def _get_parcel(self, package_id):
        pass

    @implemented_by_carrier
    def _convert_address(self, partner):
        pass

    @implemented_by_carrier
    def _error_handling(self, error_dict):
        pass
    # end of API

    # Core functions

    @api.multi
    def _roulier_generate_labels(self, package_ids=None):
        # call generate_shipping_labels for each package
        # collect answers from generate_shipping_labels
        # persist it
        self.ensure_one()

        labels = self.generate_shipping_labels(package_ids)
        for label in labels:
            data = {
                'name': label['name'],
                'res_id': self.id,
                'res_model': 'stock.picking',
            }
            if label.get('package_id'):
                data['package_id'] = label['package_id']

            if label.get('url'):
                data['url'] = label['url']
                data['type'] = 'url'
            elif label.get('data'):
                data['datas'] = label['data'].encode('base64')
                data['type'] = 'binary'

            self.env['shipping.label'].create(data)
        return True

    @api.multi
    def _roulier_generate_shipping_labels(self, package_ids=None):
        """Create as many labels as package_ids or in self."""
        self.ensure_one()
        packages = []
        if package_ids:
            packages = package_ids
        else:
            packages = self._get_packages_from_picking()
        if not packages:
            raise UserError(_('No package found for this picking'))
            # It's not our responsibility to create the packages
        labels = [
            self._call_roulier_api(package)
            for package in packages
        ]
        return labels

    def _call_roulier_api(self, package_id):
        """Create a label for a given package_id."""
        # There is low chance you need to override it.
        # Don't forget to implement _a-carrier_before_call
        # and _a-carrier_after_call
        self.ensure_one()

        roulier_instance = roulier.get(self.carrier_type)
        payload = roulier_instance.api()

        sender = self._get_sender()
        receiver = self._get_receiver()

        payload['auth'] = self._get_auth()

        payload['from_address'] = self._convert_address(sender)
        payload['to_address'] = self._convert_address(receiver)

        if self._should_include_customs(package_id):
            payload['customs'] = self._get_customs(package_id)

        payload['service'] = self._get_service(package_id)
        payload['parcel'] = self._get_parcel(package_id)

        # sorte d'interceptor ici pour que chacun
        # puisse ajouter ses merdes à payload
        payload = self._before_call(package_id, payload)
        # vrai appel a l'api
        ret = roulier_instance.get_label(payload)

        # minimum error handling
        if ret.get('status', '') == 'error':
            self._error_handling(ret)
            raise UserError(_(ret.get('message', 'WebService error')))

        # give result to someonelese
        return self._after_call(package_id, ret)

    # helpers
    @api.model
    def _roulier_convert_address(self, partner):
        """Convert a partner to an address for roulier.

        params:
            partner: a res.partner
        return:
            dict
        """
        address = {}
        extract_fields = [
            'name', 'zip', 'city', 'phone', 'mobile',
            'email', 'street1', 'street2']
        for elm in extract_fields:
            if elm in partner:
                # because a value can't be None in odoo's ORM
                # you don't want to mix (bool) False and None
                if partner._fields[elm].type != fields.Boolean.type:
                    if partner[elm]:
                        address[elm] = partner[elm]
                    # else:
                    # it's a None: nothing to do
                else:  # it's a boolean: keep the value
                    address[elm] = partner[elm]
        if partner.parent_id.is_company:
            address['company'] = partner.parent_id.name
        # Codet ISO 3166-1-alpha-2 (2 letters code)
        address['country'] = partner.country_id.code
        return self._roulier_clean_phones(address)

    def _roulier_clean_phones(self, address):
        # TODO make more cleaner with phone library
        # some prehistoric operators don't do that themselves
        for field in ['phone', 'mobile']:
            if address.get(field):
                address[field] = address[field].replace(' ', '')
        return address

    def _roulier_is_our(self):
        """Called only by non-roulier deliver methods."""
        # don't override it
        return False

    # default implementations

    # if you want to implement your carrier behavior, don't override it,
    # but define your own method instead with your carrier prefix.
    # see documentation for more details about it
    def _roulier_get_auth(self):
        """Login/password of the carrier account.

        Returns:
            a dict with login and password keys
        """
        auth = {
            'login': '',
            'password': '',
        }
        return auth

    def _roulier_get_service(self, package_id):
        shipping_date = self._get_shipping_date(package_id)

        service = {
            'product': self.carrier_code,
            'shippingDate': shipping_date,
        }
        return service

    def _roulier_get_parcel(self, package_id):
        weight = package_id.get_weight()
        parcel = {
            'weight': weight,
        }
        return parcel

    def _roulier_get_sender(self):
        """Sender of the picking (for the label).

        Return:
            (res.partner)
        """
        self.ensure_one()
        return self.company_id.partner_id

    def _roulier_get_receiver(self):
        """The guy who the shippment is for.

        At home or at a distribution point, it's always
        the same receiver address.

        Return:
            (res.partner)
        """
        self.ensure_one()
        return self.partner_id

    def _roulier_get_shipping_date(self, package_id):
        tomorrow = datetime.now() + timedelta(1)
        return tomorrow.strftime('%Y-%m-%d')

    def _roulier_get_options(self, package_id):
        return {}

    def _roulier_get_customs(self, package_id):
        return {}

    def _roulier_should_include_customs(self, package_id):
        sender = self._get_sender()
        receiver = self._get_receiver()
        return sender.country_id.code == receiver.country_id.code

    @api.model
    def _roulier_error_handling(self, error_dict):
        pass