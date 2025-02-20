import logging
import requests
import json
import csv
import os
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    to_invoice = fields.Boolean(default=True)  # Siempre forzar facturación
    fel_reference = fields.Char("FEL Referencia")
    fel_number = fields.Char("FEL Número de Factura")
    fel_authorization_number = fields.Char("FEL Número de Autorización")
    fel_certificate_date = fields.Char("FEL Fecha de Certificación")
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

    def _get_or_regenerate_token(self):
        """
        Verifica si el token ha expirado y lo regenera si es necesario.
        """
        company = self.company_id
        token_data = json.loads(company.fel_token or '{}')

        # Verificar si el token ha expirado
        _logger.info("Token data: %s", token_data)
        token_expiry = fields.Datetime.from_string(token_data.get('expira_en').replace('T', ' ').split('.')[0])
        _logger.info("Token Expiry: %s", token_expiry)
        _logger.info("Now: %s", fields.Datetime.now())
        _logger.info("Token Expiry Now?: %s", fields.Datetime.now() <= token_expiry)
        if not token_expiry or token_expiry <= fields.Datetime.now():
            _logger.info("Token ha expirado, regenerar")
            # Token ha expirado, regenerar
            api_url = "https://testapigt.digifact.com/api/login/get_token"
            username = f"GT.{company.vat.zfill(12)}.{company.fel_user}"
            payload = {
                "Username": username,
                "Password": company.fel_password
            }
            headers = {
                "Content-Type": "application/json",
            }

            try:
                response = requests.post(api_url, headers=headers, json=payload, timeout=10)
                response_data = response.json()

                if response.status_code == 200 and response_data.get("Token"):
                    # Guardar el nuevo token en la compañía
                    token_data = {
                        "Token": response_data["Token"],
                        "expira_en": response_data["expira_en"],
                        "otorgado_a": response_data["otorgado_a"]
                    }
                    company.write({'fel_token': json.dumps(token_data)})
                else:
                    raise Exception(f"Error al obtener nuevo token: {response_data.get('message')}")
            except Exception as e:
                raise Exception(f"Error al conectar con API de token: {str(e)}")

        return token_data.get('Token')

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

        # Obtener o regenerar el token
        token = self._get_or_regenerate_token()
        _logger.info("Token obtenido: %s", token)

        # Construcción del payload para la certificación en SAT
        invoice_data = {
            "usuario": sat_user,  # Usuario de la empresa en FEL
            "clave": sat_password,  # Contraseña de la empresa en FEL
            "token": token,  # Token de autenticación
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
                    "fel_number": "1234567890",
                    "fel_reference": "A",
                    "fel_authorization_number": "1234567890",
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
            self.write({"note": f"⚠ Error en certificación FEL: {str(e)}"})  # Agregar el error a las notas

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

        # Crear el directorio si no existe
        os.makedirs(os.path.dirname(file_path_csv), exist_ok=True)

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
