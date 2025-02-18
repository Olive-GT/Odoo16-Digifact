from odoo import models, fields

class PosOrder(models.Model):
    _inherit = 'pos.order'

    to_invoice = fields.Boolean(default=True)  # Asegura que siempre se genere factura

    def _prepare_invoice_vals(self):
        """Forzar siempre la generación de factura"""
        vals = super(PosOrder, self)._prepare_invoice_vals()
        vals['invoice_origin'] = self.name
        return vals
