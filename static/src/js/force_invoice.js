/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        this._super.apply(this, arguments);
        this.to_invoice = true; // Mantener la facturación activada
    },

    is_to_invoice() {
        return true; // Asegurar que siempre esté activo
    },

    toggleIsToInvoice() {
        // Evita que el usuario pueda apagar la opción
        return;
    },

    set_to_invoice(value) {
        // Forzar siempre to_invoice en true
        this.to_invoice = true;
    }
});
