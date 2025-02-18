/** @odoo-module **/

odoo.define('digifact.force_invoice', function(require) {
    "use strict";

    const { patch } = require("@web/core/utils/patch");
    const PaymentScreen = require("point_of_sale.PaymentScreen");

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
});
