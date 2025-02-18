{
    'name': 'POS Remove Invoice Button',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Oculta el botón de facturación en el POS de Odoo 16.',
    'author': 'Tu Nombre o Empresa',
    'depends': ['point_of_sale'],
    'data': ['views/assets.xml'],
    'assets': {
        'point_of_sale._assets_pos': [
            'digifact/static/src/js/remove_invoice.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
