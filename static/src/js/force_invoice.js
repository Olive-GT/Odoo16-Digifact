/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        this._super.apply(this, arguments);
        this.to_invoice = true; // Asegurar facturación siempre activada
    },

    is_to_invoice() {
        return true; // Devuelve siempre true
    },

    toggleIsToInvoice() {
        console.warn("Intento de cambiar to_invoice bloqueado."); // Debugging
        return; // Bloquea completamente el toggle en el frontend
    },

    set_to_invoice(value) {
        console.warn("Intento de cambiar set_to_invoice bloqueado."); // Debugging
        this.to_invoice = true; // Siempre mantener true
    }
});
