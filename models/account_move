from odoo import models, fields, api  # Se añade api para asegurar los @api.depends
import base64
import qrcode
from io import BytesIO

class AccountMove(models.Model):
    _inherit = 'account.move'

    qr_code = fields.Binary("Código QR", compute="_generate_qr_code_fel", store=True)
    reference = fields.Char("Referencia")
    number = fields.Char("Número de Factura")
    authorization_number = fields.Char("Número de Autorización")

    @api.depends("number", "authorization_number")  # Se asegura de regenerar el QR cuando estos campos cambien
    def _generate_qr_code_fel(self):
        for record in self:
            # Define la URL personalizada para el QR
            qr_url = f"https://olive.gt/factura/{record.id}"  # Ahora la URL usa el ID de la factura

            # Generar el código QR con la URL
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            # Convertir la imagen QR a base64 para mostrar en Odoo
            img = qr.make_image(fill='black', back_color='white')
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_code_base64 = base64.b64encode(temp.getvalue()).decode('utf-8')

            # Guardar la imagen en el campo qr_code
            record.qr_code = qr_code_base64
