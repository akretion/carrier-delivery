import setuptools

with open("VERSION.txt", "r") as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-delivery-carrier",
    description="Meta package for oca-delivery-carrier Odoo addons",
    version=version,
    install_requires=[
        "odoo12-addon-base_delivery_carrier_label",
        "odoo12-addon-delivery_auto_refresh",
        "odoo12-addon-delivery_multi_destination",
        "odoo12-addon-partner_delivery_zone",
        "odoo12-addon-stock_picking_delivery_info_computation",
    ],
    classifiers=["Programming Language :: Python", "Framework :: Odoo",],
)
