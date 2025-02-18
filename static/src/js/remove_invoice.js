/** @odoo-module **/
import { PosOrderScreen } from "@point_of_sale/app/screens/order_screen/order_screen";
import { patch } from "@web/core/utils/patch";

// Parcheamos el OrderScreen para ocultar el botón de facturación
patch(PosOrderScreen.prototype, {
    setup() {
        this._super.apply(this, arguments);
    },
    get orderButtons() {
        return this._super().filter(button => button.name !== "InvoiceButton");
    },
});
