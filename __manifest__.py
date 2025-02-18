{
    'name': 'POS Remove Invoice Button',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Elimina el botón de facturación en el POS.',
    'author': 'Olive Tech',
    'depends': ['point_of_sale'],
    'data': ['views/assets.xml'],
    'assets': {
        'point_of_sale.assets': [
            'pos_remove_invoice_button/static/src/js/remove_invoice.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
