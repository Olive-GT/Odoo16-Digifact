from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    fel_user = fields.Char("Usuario FEL")
    fel_password = fields.Char("Contraseña FEL")
    fel_token = fields.Char("Token de Certificación")
    regimen_ISR = fields.Selection([
        ('none', 'Ninguno'),
        ('quarterly', 'Trimestral'),
        ('monthly', 'Mensual')
    ], string="Régimen ISR")
