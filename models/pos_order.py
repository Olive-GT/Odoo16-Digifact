import logging
import requests
import json
import csv
import os
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = ['pos.order', 'mail.thread']

    to_invoice = fields.Boolean(default=True)  # Siempre forzar facturación
    fel_certification_number = fields.Char("Número de Certificación FEL")
    fel_series = fields.Char("Serie FEL")
    fel_uuid = fields.Char("UUID FEL")  # Número único de certificación
    fel_certificate_date = fields.Datetime("Fecha de Certificación FEL")
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

    def _prepare_fel_invoice_data(self):
        """
        Prepara la información necesaria para certificar la factura en la API de la SAT.
        """
        self.ensure_one()  # Aseguramos que solo estamos procesando un pedido

        # Obtener las credenciales de la compañía
        company = self.company_id
        sat_user = company.fel_user
        sat_password = company.fel_password

        # Validar que la empresa tenga credenciales configuradas
        if not sat_user or not sat_password:
            raise ValueError("Faltan credenciales de FEL en la configuración de la empresa.")

        # Construcción del payload para la certificación en SAT
        invoice_data = {
            "usuario": sat_user,  # Usuario de la empresa en FEL
            "clave": sat_password,  # Contraseña de la empresa en FEL
            "nit_emisor": company.vat,  # NIT de la empresa emisora
            "nombre_emisor": company.name,  # Nombre de la empresa emisora
            "direccion_emisor": company.street,  # Dirección de la empresa emisora
            "nit_receptor": self.partner_id.vat or "CF",  # NIT del cliente (CF si es consumidor final)
            "nombre_receptor": self.partner_id.name,  # Nombre del cliente
            "fecha_emision": fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Fecha actual
            "moneda": self.currency_id.name,  # Moneda de la factura
            "monto_total": self.amount_total,  # Total de la factura
            "productos": [  # Detalle de los productos vendidos
                {
                    "descripcion": line.product_id.name,
                    "cantidad": line.qty,
                    "precio_unitario": line.price_unit,
                    "subtotal": line.price_subtotal,
                } for line in self.lines
            ],
        }

        return invoice_data

    def _certify_invoice_with_sat(self):
        """
        Envía la información de la factura a la API de la SAT y devuelve la respuesta con los datos de certificación.
        """
        self.ensure_one()

        # Preparamos los datos de la factura
        invoice_data = self._prepare_fel_invoice_data()

        # Definir la URL de la API de la SAT (actualízala según corresponda)
        api_url = "https://api.sat.gob.gt/facturacion/certificar"

        # Definir los headers de la solicitud
        headers = {
            "Content-Type": "application/json",
        }

        _logger.info("Datos de la factura a enviar a SAT: %s", invoice_data)
        return {
                    "fel_certification_number": "1234567890",
                    "fel_series": "A",
                    "fel_uuid": "1234567890",
                    "fel_certificate_date": "2021-01-01 12:00:00"
                }

        try:
            # Enviar la solicitud POST a la API de la SAT
            response = requests.post(api_url, headers=headers, json=invoice_data, timeout=10)
            response_data = response.json()

            # Si la certificación es exitosa, devolvemos los datos de certificación
            if response.status_code == 200 and response_data.get("success"):
                return {
                    "fel_certification_number": response_data.get("certification_number"),
                    "fel_series": response_data.get("series"),
                    "fel_uuid": response_data.get("uuid"),
                    "fel_certificate_date": response_data.get("certificate_date")
                }
            else:
                raise Exception(f"Error en certificación FEL: {response_data.get('message')}")
        except Exception as e:
            raise Exception(f"Error al conectar con API FEL: {str(e)}")

    def _create_invoice(self, move_vals):
        """
        Modifica la función original de Odoo para enviar la factura a la SAT antes de guardarla en Odoo.
        """
        self.ensure_one()

        try:
            # 🔹 Enviar factura a la API SAT y obtener datos de certificación
            certification_data = self._certify_invoice_with_sat()

            # 🔹 Llamamos a la función original de Odoo para crear la factura
            new_move = super(PosOrder, self)._create_invoice(move_vals)

            # 🔹 Guardamos los datos de certificación en la factura creada
            new_move.write(certification_data)  # Guarda datos en `account.move`
            self.write(certification_data)  # Guarda datos en `pos.order`

            return new_move

        except Exception as e:
            _logger.error(f"❌ Error en la certificación FEL: {str(e)}")

            # 🔹 Guardar el pedido en estado "error"
            self.write({"state": "error"})
            self.message_post(body=f"⚠ Error en certificación FEL: {str(e)}")

            # 🔹 Exportar el pedido fallido a CSV y JSON
            self._export_failed_order(str(e))

            # 🔹 Guardar la orden en estado de error para recuperación posterior
            self.env.cr.commit()

            raise ValueError(f"Error en la certificación FEL: {str(e)}")

    def _export_failed_order(self, error_message):
        """
        Guarda los pedidos con error en un archivo CSV y JSON.
        """
        file_path_csv = "/opt/odoo/custom_addons/digifact/data/failed_orders.csv"
        file_path_json = "/opt/odoo/custom_addons/digifact/data/failed_orders.json"

        # Datos del pedido
        order_data = {
            "order_name": self.name,
            "pos_reference": self.pos_reference,
            "customer": self.partner_id.name if self.partner_id else "Sin Cliente",
            "amount_total": self.amount_total,
            "error_message": error_message
        }

        # Guardar en CSV
        file_exists = os.path.isfile(file_path_csv)
        with open(file_path_csv, mode="a", newline="") as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Order Name", "POS Reference", "Customer", "Amount Total", "Error Message"])
            writer.writerow(order_data.values())

        # Guardar en JSON
        try:
            with open(file_path_json, "r") as json_file:
                failed_orders = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError):
            failed_orders = []

        failed_orders.append(order_data)

        with open(file_path_json, "w") as json_file:
            json.dump(failed_orders, json_file, indent=4)

        _logger.info(f"📂 Pedido con error guardado en {file_path_csv} y {file_path_json}")