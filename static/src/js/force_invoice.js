/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    setup() {
        this._super.apply(this, arguments);
        console.warn("Forzando to_invoice=True en todas las órdenes.");
        const order = this.env.pos.get_order();
        if (order) {
            order.set_to_invoice(true);
        }
    },

    toggleIsToInvoice() {
        console.warn("Intento de cambiar to_invoice bloqueado!");
        return; // Bloquea el botón, no permite cambios
    }
});
