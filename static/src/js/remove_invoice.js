/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        this._super.apply(this, arguments);
        this.isToInvoice = false; // Deshabilita la opción de facturación
    },
});

// Ocultar el botón en la interfaz
patch(Order, "remove_invoice_button", (Order) => {
    Order.prototype.init = function () {
        this._super.apply(this, arguments);
        this.isToInvoice = false; // Desactiva la opción de facturación
    };
});
