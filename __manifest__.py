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
        'views/partner_details_edit_inherit.xml'
        ],
    'assets': {
        'point_of_sale._assets_pos': [
            'digifact/static/src/js/force_invoice.js',
            'digifact/static/src/css/hide_invoice.css',
            'custom_module/static/src/xml/partner_details_edit_extend.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
