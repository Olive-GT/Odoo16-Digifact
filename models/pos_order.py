import logging
import requests
import json
import base64
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    to_invoice = fields.Boolean(default=True)  # Siempre forzar facturación
    certified = fields.Boolean("Certificado FEL", default=False)
    fel_reference = fields.Char("FEL Referencia")
    fel_number = fields.Char("FEL Número de Factura")
    fel_authorization_number = fields.Char("FEL Número de Autorización")
    fel_certificate_date = fields.Char("FEL Fecha de Certificación")
    certified = fields.Boolean("Certificado FEL", default=False)
    note = fields.Text("Nota")
    state = fields.Selection(selection_add=[('error', 'Error en Certificación')])  # Nuevo estado

    @api.model
    def create(self, vals):
        """Asegurar que todas las órdenes se creen con to_invoice=True"""
        vals['to_invoice'] = True
        return super(PosOrder, self).create(vals)

    def write(self, vals):
        """Evita que to_invoice sea cambiado a False"""
        if 'to_invoice' in vals and not vals['to_invoice']:
            vals['to_invoice'] = True
        return super(PosOrder, self).write(vals)

    def _create_invoice(self, move_vals):
        """
        Modifica la función original de Odoo para enviar la factura a la SAT antes de guardarla en Odoo.
        """
        self.ensure_one()

        # 🔹 Llamamos a la función original de Odoo para crear la factura
        new_move = super(PosOrder, self)._create_invoice(move_vals)
        new_move.pos_config_id = self.session_id.config_id.id

        # 🔹 Obtener la lista de compañías permitidas para certificar
        allowed_companies_str = self.env['ir.config_parameter'].sudo().get_param('certify_allowed_companies', '')
        allowed_companies = [int(company_id) for company_id in allowed_companies_str.split(',') if company_id]

        if self.company_id.id not in allowed_companies:
            _logger.info(f"🔒 La compañía {self.company_id.name} no está permitida para certificar facturas.")
            return new_move

        try:
            # 🔹 Enviar factura a la API SAT y obtener datos de certificación
            pos_config = self.session_id.config_id
            certification_data = new_move._certify_invoice_with_sat(pos_config)
            certification_data['certified'] = True
        except Exception as e:
            _logger.error(f"❌ Error en la certificación FEL: {str(e)}")
            certification_data = {
                "fel_number": "",
                "fel_reference": "",
                "fel_authorization_number": "",
                "fel_certificate_date": "",
                "note": f"⚠ Error en certificación FEL: {str(e)}",
                "certified": False
            }

        # 🔹 Guardamos los datos de certificación en la factura creada
        new_move.write(certification_data)  # Guarda datos en `account.move`
        self.write(certification_data)  # Guarda datos en `pos.order`
        self.flush_model()  # Forzar la escritura de los datos en la base de datos

        # 🔹 Agregar fel_reference-fel_number al inicio de la referencia de la factura
        if new_move.ref:
            new_move.ref = f"{certification_data['fel_reference']}-{certification_data['fel_number']} ({new_move.ref})"
        else:
            new_move.ref = f"{certification_data['fel_reference']}-{certification_data['fel_number']}"

        # 🔹 Establecer el campo tipo_gasto de la factura a "compra"
        new_move.tipo_gasto = "compra"

        # 🔹 Enviar correo electrónico si la certificación falló
        if not certification_data['certified']:
            # 🔹 Verifica que el pedido tiene datos correctos
            order_name = self.name or "Pedido desconocido"
            order_note = certification_data.get("note", "No hay detalles disponibles")

            # 🔹 Crea el contenido del correo
            email_body = f"""
                <p><strong>ERROR DE CERTIFICACIÓN</strong></p>
                <p><strong>Pedido:</strong> {order_name}</p>
                <p><strong>Detalles del error:</strong> {order_note}</p>
                <p>Por favor, revise y solucione el problema.</p>
                <p>Saludos,</p>
                <p>El equipo de soporte</p>
            """

            # 🔹 Crea y envía el correo
            # Obtener el correo electrónico del destinatario desde la configuración del sistema
            email_to = self.env['ir.config_parameter'].sudo().get_param('fel_error_email', 'juancarlos@olivegt.com')

            mail_values = {
                'subject': f"Error en Certificación FEL para la Orden {order_name}",
                'email_from': self.env.user.email or 'noreply@tuempresa.com',
                'email_to': email_to,  # Utilizar el correo configurado
                'body_html': email_body,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

            _logger.info(f"📩 Correo enviado a juancarlos@olivegt.com con contenido:\n{email_body}")

        return new_move

    import base64

    def _add_mail_attachment(self, name, ticket):
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': self.ids[0],
            'mimetype': 'image/jpeg',
        })
        attachment = [(4, receipt.id)]

        # Verificar si el pedido tiene una factura (account_move)
        if self.mapped('account_move'):
            invoice = self.account_move
            if invoice.certified:
                # Si la factura está certificada, se adjunta el PDF
                report = self.env['ir.actions.report']._render_qweb_pdf("account.account_invoices", invoice.ids[0])
                filename = name + '.pdf'
                invoice_attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(report[0]),
                    'res_model': 'pos.order',
                    'res_id': self.ids[0],
                    'mimetype': 'application/x-pdf'
                })
                attachment += [(4, invoice_attachment.id)]

        return attachment

    def _prepare_mail_values(self, name, client, ticket):
        message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client['name'], name)

        invoice = self.account_move
        invoice.send_email_to = client['email']

        return {
            'subject': _('Receipt %s', name),
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': client['email'],
            'attachment_ids': self._add_mail_attachment(name, ticket),
        }