/** @odoo-module **/

odoo.define('digifact.force_invoice', function(require) {
    "use strict";

    const { patch } = require("@web/core/utils/patch");
    const PaymentScreen = require("point_of_sale.PaymentScreen");
    const { Gui } = require("point_of_sale.Gui");
    const { useService } = require("@web/core/utils/hooks");

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
        },

        async _finalizeValidation() {
            try {
                // Intenta finalizar la validación del pedido
                await this._super.apply(this, arguments);
            } catch (error) {
                console.error("Error al validar el pedido:", error);

                // Generar y descargar el PDF del pedido
                const order = this.env.pos.get_order();
                if (order) {
                    const receipt = order.export_for_printing();
                    const receiptHtml = await this._renderReceipt(receipt);

                    // Crear un Blob con el contenido del PDF
                    const blob = new Blob([receiptHtml], { type: "application/pdf" });
                    const url = URL.createObjectURL(blob);

                    // Forzar la descarga del PDF
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = `Pedido_${order.name}.pdf`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }

                // Mostrar un mensaje de error al usuario
                Gui.showPopup("ErrorPopup", {
                    title: "Error en el pedido",
                    body: "Ocurrió un error al procesar el pedido. Se ha descargado un PDF del pedido para su revisión.",
                });
            }
        },

        async _renderReceipt(receipt) {
            // Renderizar el HTML del recibo
            const receiptHtml = await this.env.pos.qweb.renderToString("point_of_sale.Receipt", {
                receipt: receipt,
                widget: this,
            });
            return receiptHtml;
        },
    });
});