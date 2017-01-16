# coding: utf-8
# © 2016 Raphael REVERDY <raphael.reverdy@akretion.com>
#        David BEAL <david.beal@akretion.com>
#        Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Delivery Carrier TRS (fr)',
    'version': '9.0.1.0.0',
    'author': 'Akretion, Odoo Community Association (OCA)',
    'summary': 'Generate Label for TRS',
    'maintainer': 'Akretion, Odoo Community Association (OCA)',
    'category': 'Warehouse',
    'depends': [
        'delivery_roulier',
        'base_phone',
        # 'attachment_base_synchronize',
        'delivery_carrier_deposit'
    ],
    'website': 'http://www.akretion.com/',
    'data': [
        'data/delivery.xml',
        'data/keychain.xml',
    ],
    'external_dependencies': {
        'python': [
            'roulier',
        ]
    },
    'installable': True,
    'license': 'AGPL-3',
}