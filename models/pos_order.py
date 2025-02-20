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
        token_expiry = fields.Datetime.context_timestamp(self, token_expiry)
        now = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        _logger.info("Token Expiry: %s", token_expiry)
        _logger.info("Now: %s", now)
        _logger.info("Token Expiry Now?: %s", now >= token_expiry)
        if not token_expiry or now >= token_expiry:
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
            "moneda": "GTQ",  # Token de autenticación
            "nit_emisor": company.vat,  # NIT de la empresa emisora
            "nombre_emisor": company.name,  # Nombre de la empresa emisora
            "nombre_establecimiento": "NAPARI",  # Nombre de la empresa emisora
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

        # Generar el XML de la factura
        invoice_xml = self._generate_invoice_xml(invoice_data)

        _logger.info("Datos de la factura a enviar a SAT: %s", invoice_xml)

        # Definir la URL de la API de la SAT (actualízala según corresponda)
        api_url = f"https://testapigt.digifact.com/api/FelRequestV2?NIT={invoice_data['nit_emisor']}&TIPO=CERTIFICATE_DTE_XML_TOSIGN&FORMAT=XML&USERNAME={invoice_data['usuario']}"

        # Definir los headers de la solicitud
        headers = {
            "Content-Type": "application/xml",
            "Authorization": invoice_data['token'],
        }

        _logger.info("Datos de la factura a enviar a SAT: %s", invoice_xml)

        try:
            # Enviar la solicitud POST a la API de la SAT
            response = requests.post(api_url, headers=headers, data=invoice_xml, timeout=10)
            response_data = response.json()

            # Si la certificación es exitosa, devolvemos los datos de certificación
            if response.status_code == 200 and response_data.get("success"):
                return {
                    "fel_number": response_data.get("certification_number"),
                    "fel_reference": response_data.get("series"),
                    "fel_authorization_number": response_data.get("uuid"),
                    "fel_certificate_date": response_data.get("certificate_date")
                }
            else:
                raise Exception(f"Error en certificación FEL: {response_data.get('message')}")
        except Exception as e:
            raise Exception(f"Error al conectar con API FEL: {str(e)}")

    def _generate_invoice_xml(self, invoice_data):
        """
        Genera el XML de la factura a partir de los datos proporcionados.
        """
        # Ejemplo de XML, se debe ajustar según los requisitos de la SAT
        invoice_xml = f"""<?xml version='1.0' encoding='UTF-8'?>
<dte:GTDocumento xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:dte="http://www.sat.gob.gt/dte/fel/0.2.0" Version="0.1">
    <dte:SAT ClaseDocumento="dte">
        <dte:DTE ID="DatosCertificados">
            <dte:DatosEmision ID="DatosEmision">
                <dte:DatosGenerales Tipo="FACT" FechaHoraEmision="{invoice_data['fecha_emision']}"
                    CodigoMoneda="{invoice_data['moneda']}" />
                <dte:Emisor NITEmisor="{invoice_data['nit_emisor']}" NombreEmisor="{invoice_data['nombre_emisor']}" CodigoEstablecimiento="1"
                    NombreComercial="{invoice_data['nombre_establecimiento']}" AfiliacionIVA="GEN">
                    <dte:DireccionEmisor>
                        <dte:Direccion>{invoice_data['direccion_emisor']}</dte:Direccion>
                        <dte:CodigoPostal>0100</dte:CodigoPostal>
                        <dte:Municipio>GUATEMALA</dte:Municipio>
                        <dte:Departamento>GUATEMALA</dte:Departamento>
                        <dte:Pais>GT</dte:Pais>
                    </dte:DireccionEmisor>
                </dte:Emisor>
                <dte:Receptor NombreReceptor="{invoice_data['nombre_receptor']}" IDReceptor="{invoice_data['nit_receptor']}">
                    <dte:DireccionReceptor>
                        <dte:Direccion>GUATEMALA</dte:Direccion>
                        <dte:CodigoPostal>01010</dte:CodigoPostal>
                        <dte:Municipio>GUATEMALA</dte:Municipio>
                        <dte:Departamento>GUATEMALA</dte:Departamento>
                        <dte:Pais>GT</dte:Pais>
                    </dte:DireccionReceptor>
                </dte:Receptor>
                <dte:Frases>
                    <dte:Frase TipoFrase="1" CodigoEscenario="2"/>
                </dte:Frases>
                <dte:Items>
                    {"".join([f'''
                    <dte:Item NumeroLinea="{i+1}" BienOServicio="B">
                        <dte:Cantidad>{p['cantidad']}</dte:Cantidad>
                        <dte:UnidadMedida>CA</dte:UnidadMedida>
                        <dte:Descripcion>{p['descripcion']}</dte:Descripcion>
                        <dte:PrecioUnitario>{p['precio_unitario']}</dte:PrecioUnitario>
                        <dte:Precio>{p['subtotal']}</dte:Precio>
                        <dte:Descuento>0</dte:Descuento>
                        <dte:Impuestos>
                            <dte:Impuesto>
                                <dte:NombreCorto>IVA</dte:NombreCorto>
                                <dte:CodigoUnidadGravable>1</dte:CodigoUnidadGravable>
                                <dte:MontoGravable>{p['subtotal'] * 0.89}</dte:MontoGravable>
                                <dte:MontoImpuesto>{p['subtotal'] * 0.12}</dte:MontoImpuesto>
                            </dte:Impuesto>
                        </dte:Impuestos>
                        <dte:Total>{p['subtotal']}</dte:Total>
                    </dte:Item>''' for i, p in enumerate(invoice_data['productos'])])}
                </dte:Items>
                <dte:Totales>
                    <dte:TotalImpuestos>
                        <dte:TotalImpuesto NombreCorto="IVA" TotalMontoImpuesto="{sum(p['subtotal'] * 0.12 for p in invoice_data['productos'])}"/>
                    </dte:TotalImpuestos>
                    <dte:GranTotal>{invoice_data['monto_total']}</dte:GranTotal>
                </dte:Totales>
            </dte:DatosEmision>
        </dte:DTE>
    </dte:SAT>
</dte:GTDocumento>"""
        return invoice_xml.strip()

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
