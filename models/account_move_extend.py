from odoo import models, fields, api
import base64
import qrcode
from io import BytesIO

class AccountMove(models.Model):
    _inherit = 'account.move'

    qr_code = fields.Binary("Código QR", compute="_compute_qr_code_fel", store=True)
    reference = fields.Char("Referencia")
    number = fields.Char("Número de Factura")
    authorization_number = fields.Char("Número de Autorización")

    @api.depends("number", "authorization_number")  
    def _compute_qr_code_fel(self):
        """ Genera el código QR cada vez que se cambia el número de factura o autorización """
        for record in self:
            record.qr_code = record._generate_qr_code_fel()

    def _generate_qr_code_fel(self):
        """ Método que puede ser llamado en QWeb para obtener el QR """
        # Si no hay número o autorización, retornar vacío
        if not self.number or not self.authorization_number:
            return ""

        # Definir la URL personalizada para el QR
        qr_url = f"https://olive.gt/factura/{self.number}/{self.authorization_number}"

        # Generar el código QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Convertir la imagen QR a base64
        img = qr.make_image(fill='black', back_color='white')
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_code_base64 = base64.b64encode(temp.getvalue()).decode('utf-8')

        return qr_code_base64
