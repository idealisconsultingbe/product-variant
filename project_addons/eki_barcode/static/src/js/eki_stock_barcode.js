odoo.define('eki_barcode.stock_barcode', function (require) {
    "use strict";

    var core = require('web.core');
    var barcode_menu = require('stock_barcode.MainMenu');

    barcode_menu.MainMenu = barcode_menu.MainMenu.extend({
        /**
         * Extend existing events to add new product_lot button event management
         */
        events: _.extend({}, barcode_menu.MainMenu.prototype.events, {
            "click .button_product_lot": function() {
                this.open_product_lot();
            },
        }),

        open_product_lot: function () {
            var self = this;
            return this._rpc({
                    model: 'eki.product.lot',
                    method: 'open_product_lot_action',
                })
                .then(function(result) {
                    self.do_action(result);
                });
        },
    });

    core.action_registry.add('stock_barcode_main_menu', barcode_menu.MainMenu);

});
