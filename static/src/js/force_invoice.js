/** @odoo-module **/

odoo.define('digifact.force_invoice', function(require) {
    "use strict";

    const { patch } = require("@web/core/utils/patch");
    const { PaymentScreen } = require("point_of_sale/app/screens/payment_screen/payment_screen");

    patch(PaymentScreen.prototype, "digifact_patch_force_invoice", {
        setup() {
            this._super.apply(this, arguments);
            console.warn("Forzando to_invoice=True en todas las órdenes.");
            const order = this.env.pos.get_order();
            if (order) {
                order.set_to_invoice(true);
                this.render(true); // 👈 FORZAR ACTUALIZACIÓN DE LA UI
            }
        },

        toggleIsToInvoice() {
            console.warn("Intento de cambiar to_invoice bloqueado!");
            return; // Bloquea el botón, no permite cambios
        },

        shouldDownloadInvoice() {
            console.warn("Descarga de factura bloqueada!");
            return false; // Bloquea la descarga automática de facturas
        }
    });
});
