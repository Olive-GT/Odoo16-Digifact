/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerDetailsEdit } from "@point_of_sale/js/Screens/PartnerDetailsEdit/PartnerDetailsEdit";
import rpc from 'web.rpc';

patch(PartnerDetailsEdit.prototype, "digifact.partner_vat_verification", {
    async verifyVAT() {
        const vatNumber = this.changes.vat || '';

        if (!vatNumber.trim()) {
            await this.showPopup("ErrorPopup", {
                title: "Error",
                body: "Por favor, ingrese un NIT antes de verificar.",
            });
            return;
        }

        try {
            this.env.services.ui.block();

            const session = this.env.pos ? this.env.pos.config : null;
            const company_id = session ? session.company_id[0] : this.env.company.id;

            const result = await rpc('/web/dataset/call_kw', {
                model: 'res.partner',
                method: 'verify_nit',
                args: [vatNumber, company_id],
            });

            if (result.valid) {
                this.changes.name = result.company_name || this.changes.name;
                this.changes.street = result.address || this.changes.street;
                await this.render();
            } else {
                await this.showPopup("ErrorPopup", {
                    title: "NIT inválido",
                    body: result.error || "No se encontró información para este NIT.",
                });
            }
        } catch (error) {
            console.error("Error al verificar el NIT:", error);
            await this.showPopup("ErrorPopup", {
                title: "Error del Servidor",
                body: "Ocurrió un error al comunicarse con el servidor.",
            });
        } finally {
            this.env.services.ui.unblock();
        }
    }
});