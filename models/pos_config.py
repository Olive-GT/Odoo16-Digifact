from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    establishment_name = fields.Char("Nombre del Establecimiento")
    establishment_id = fields.Char("ID del Establecimiento")
