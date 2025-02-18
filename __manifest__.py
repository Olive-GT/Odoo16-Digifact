{
    'name': 'POS Facturación Obligatoria',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Forza la facturación en el POS de Odoo 16, evitando ventas sin factura.',
    'author': 'Olive Tech',
    'depends': ['point_of_sale'],
    'data': ['views/assets.xml'],
    'assets': {
        'point_of_sale._assets_pos': [
            'digifact/static/src/js/force_invoice.js',
            'digifact/static/src/css/hide_invoice.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
