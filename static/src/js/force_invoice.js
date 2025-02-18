/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PaymentScreen.prototype, {
    toggleIsToInvoice() {
        console.warn("Intento de cambiar to_invoice bloqueado!");
        return; // Bloquea el botón, no permite cambios
    },

    get currentOrder() {
        const order = this.env.pos.get_order();
        console.warn("Interceptando currentOrder: ", order);
        if (order) {
            order.set_to_invoice(true); // Usamos el método correcto para activar facturación
        }
        return order;
    }
});
