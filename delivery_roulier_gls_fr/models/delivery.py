# © 2015 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models

from .quant_package import URL_TRACKING


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("gls_fr_glsbox", "GLS France")],
        ondelete={"gls_fr_glsbox": "set default"},
    )

    def gls_fr_glsbox_get_tracking_link(self, picking):
        return URL_TRACKING % picking.carrier_tracking_ref
