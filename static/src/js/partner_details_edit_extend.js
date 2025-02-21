/** @odoo-module **/

if (!odoo.hasOwnProperty("digifact_partner_vat_verification_loaded")) {
    odoo.define("digifact.partner_vat_verification", function (require) {
        "use strict";

        const { patch } = require("@web/core/utils/patch");
        const PartnerDetailsEdit = require("point_of_sale.PartnerDetailsEdit");

        patch(PartnerDetailsEdit.prototype, "digifact_patch_partner_vat", {
            setup() {
                this._super.apply(this, arguments);
                console.warn("Extensión de PartnerDetailsEdit cargada correctamente.");
            },

            async verifyVAT() {
                console.warn("Ejecutando verificación de VAT...");

                const vatNumber = this.changes.vat || this.props.partner.vat;
                if (!vatNumber) {
                    this.showPopup("ErrorPopup", {
                        title: "Error",
                        body: "Por favor, ingrese un NIF antes de verificar.",
                    });
                    return;
                }

                try {
                    const result = await this.rpc("/pos/vat/verify", { vat: vatNumber });

                    if (result.valid) {
                        this.changes.name = result.company_name || this.changes.name;
                        this.changes.street = result.address || this.changes.street;
                        this.changes.city = result.city || this.changes.city;
                        this.changes.country_id = result.country_id || this.changes.country_id;

                        this.render(true);
                    } else {
                        this.showPopup("ErrorPopup", {
                            title: "VAT Inválido",
                            body: "El NIF ingresado no es válido.",
                        });
                    }
                } catch (error) {
                    this.showPopup("ErrorPopup", {
                        title: "Error de Conexión",
                        body: "No se pudo verificar el NIF. Intente más tarde.",
                    });
                }
            }
        });

        // Marcar como cargado para evitar duplicación
        odoo.digifact_partner_vat_verification_loaded = true;
    });
}
