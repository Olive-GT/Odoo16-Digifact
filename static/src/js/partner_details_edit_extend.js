/** @odoo-module **/

if (!odoo.__loaded_partner_vat_verification__) {
    odoo.__loaded_partner_vat_verification__ = true;

    odoo.define("digifact.partner_vat_verification", function (require) {
        "use strict";

        const { patch } = require("@web/core/utils/patch");
        const PartnerDetailsEdit = require("point_of_sale.PartnerDetailsEdit");
        const rpc = require("web.rpc");

        patch(PartnerDetailsEdit.prototype, "digifact_patch_partner_vat", {
            async verifyVAT() {
                console.warn("🔍 Ejecutando verificación de NIT...");

                const vatNumber = this.changes.vat || this.props.partner.vat;

                // 📌 Verificar si el usuario ingresó un NIT válido
                if (!vatNumber || vatNumber.trim() === "") {
                    this.showPopup("ErrorPopup", {
                        title: "Error",
                        body: "Por favor, ingrese un NIT antes de verificar.",
                    });
                    return;
                }

                this.env.services.ui.block();

                try {
                    const session = this.env.pos ? this.env.pos.config : null;
                    const company_id = session ? session.company_id[0] : this.env.company.id;

                    const result = await rpc.query({
                        model: "res.partner",
                        method: "verify_nit",
                        args: [vatNumber, company_id],
                    });

                    this.env.services.ui.unblock();

                    if (result.valid) {
                        console.warn("✅ NIT válido, actualizando datos del cliente...");

                        // 📌 Rellenar automáticamente los datos en la UI
                        this.changes.name = result.company_name || this.changes.name;
                        this.changes.street = result.address || this.changes.street;
                        
                        // 📌 Forzar actualización de la UI
                        this.render(true);
                    } else {
                        this.showPopup("ErrorPopup", {
                            title: "Error en la verificación",
                            body: result.error || "NIT inválido.",
                        });
                    }
                } catch (error) {
                    this.env.services.ui.unblock();
                    
                    console.error("❌ Error al verificar el NIT:", error);
                    this.showPopup("ErrorPopup", {
                        title: "Error de Conexión",
                        body: "No se pudo verificar el NIT. Intente más tarde.",
                    });
                }
            }
        });
    });
}