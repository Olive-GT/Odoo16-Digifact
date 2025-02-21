import logging
import requests
import json
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_or_regenerate_token(self):
        """Verifica si el token ha expirado y lo regenera si es necesario."""
        company = self.env.company
        token_data = json.loads(company.fel_token or '{}')

        token_expiry = token_data.get('expira_en')
        if token_expiry:
            token_expiry = fields.Datetime.from_string(token_expiry.replace('T', ' ').split('.')[0])
            token_expiry = fields.Datetime.context_timestamp(self, token_expiry)
            now = fields.Datetime.context_timestamp(self, fields.Datetime.now())

            if now < token_expiry:
                return token_data.get('Token')

        _logger.info("🔄 Token ha expirado, regenerando...")

        # Obtener URL del API de autenticación
        api_url = self.env['ir.config_parameter'].sudo().get_param('fel_token_url')
        if not api_url:
            raise Exception("❌ URL de API de token no configurada en parámetros del sistema.")

        # Construir payload con credenciales
        username = f"GT.{company.vat.zfill(12)}.{company.fel_user}"
        payload = {
            "Username": username,
            "Password": company.fel_password
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=10)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("Token"):
                token_data = {
                    "Token": response_data["Token"],
                    "expira_en": response_data["expira_en"],
                    "otorgado_a": response_data["otorgado_a"]
                }
                company.write({'fel_token': json.dumps(token_data)})
                return response_data["Token"]
            else:
                _logger.error(f"❌ Error al obtener nuevo token: {response_data}")
                raise Exception(f"Error al obtener nuevo token: {response_data.get('message')}")
        except Exception as e:
            _logger.error(f"❌ Error al conectar con API de token: {str(e)}")
            raise Exception(f"Error al conectar con API de token: {str(e)}")

    @api.model
    def verify_nit(self, vat):
        """Verifica un NIT usando el API de Digifact."""

        # Obtener o regenerar el token
        token = self._get_or_regenerate_token()
        _logger.info("🔑 Token obtenido correctamente.")

        # Obtener URL del API desde los parámetros del sistema
        api_url = self.env['ir.config_parameter'].sudo().get_param('fel_nit_validation_url')
        if not api_url:
            raise Exception("❌ URL de API de validación de NIT no configurada en parámetros del sistema.")

        # Obtener datos de la compañía
        company = self.env.company
        username = company.fel_user

        # Construir parámetros de consulta
        params = {
            "NIT": company.vat.zfill(12),
            "DATA1": "SHARED_GETINFONITcom",
            "DATA2": f"NIT|{vat}",
            "USERNAME": username
        }

        _logger.info("Request %s", params)
        
        headers = {
            "Authorization": token,
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            _logger.info("📩 Respuesta del API: %s", json.dumps(data, indent=2))

            # Manejar respuesta negativa
            if "Message" in data:
                return {"valid": False, "error": data["Message"]}

            if "REQUEST" in data and data["REQUEST"][0]["Respuesta"] == 0:
                return {"valid": False, "error": data["REQUEST"][0]["Mensaje"]}

            # Extraer información si el NIT es válido
            if "RESPONSE" in data and data["RESPONSE"][0]["NIT"]:
                return {
                    "valid": True,
                    "company_name": data["RESPONSE"][0].get("NOMBRE", ""),
                    "address": data["RESPONSE"][0].get("Direccion", ""),
                }

            return {"valid": False, "error": "El NIT no tiene información disponible"}

        except requests.exceptions.RequestException as e:
            _logger.error("❌ Error en la consulta del NIT: %s", str(e))
            return {"valid": False, "error": "No se pudo conectar con el API"}
