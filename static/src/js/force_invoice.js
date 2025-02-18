/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        this._super.apply(this, arguments);
        this.to_invoice = true; // Forzar siempre la facturación
    },

    is_to_invoice() {
        return true; // Siempre devuelve true, obligando a la facturación
    },

    toggleIsToInvoice() {
        // Evita que el usuario pueda desactivar la opción de facturación
        return;
    }
});
