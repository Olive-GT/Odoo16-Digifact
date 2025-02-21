import { PosComponent } from "@point_of_sale/app/component";
import { useListener } from "@web/core/utils/hooks";

export class PartnerDetailsEditExtend extends PosComponent {
    setup() {
        super.setup();
        useListener("click", this.verifyVAT);
    }

    async verifyVAT() {
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
}
