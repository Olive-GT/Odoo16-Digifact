{
    'name': 'POS Facturación Obligatoria',
    'version': '16.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Forza la facturación en el POS de Odoo 16, evitando ventas sin factura.',
    'author': 'Olive Tech',
    'depends': ['point_of_sale'],
    'data': [
        'views/assets.xml',
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'views/pos_order_views.xml',
        'views/pos_config_views.xml',
        ],
    'assets': {
        'point_of_sale._assets_pos': [
            'digifact/static/src/js/force_invoice.js',
            'digifact/static/src/css/hide_invoice.css',
        ],
        'point_of_sale.assets': [
            'digifact/static/src/xml/partner_details_edit.xml',
            'digifact/static/src/css/partner_details_edit.css',
            'digifact/static/src/js/partner_details_edit_extend.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
