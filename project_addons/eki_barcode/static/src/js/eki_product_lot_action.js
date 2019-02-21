odoo.define('eki_barcode.ProductLotClientAction', function (require) {
    "use strict";

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var ViewsWidget = require('stock_barcode.ViewsWidget');
    var HeaderWidget = require('stock_barcode.HeaderWidget');

    var ProductLotClientAction = AbstractAction.extend({
        className: 'o_barcode_client_action',

        custom_events: {
            reload: '_onReload',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
        },

        start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.headerWidget = new HeaderWidget(self);
                self.view = new ViewsWidget(
                    self,
                    'eki.product.lot',
                    'eki_barcode.eki_product_lot_barcode_form_view',
                    {},
                    false
                );
                self.headerWidget.prependTo(self.$el);
                self.view.appendTo(self.$el);
            }).then(function() {
                self.headerWidget.toggleDisplayContext('specialized');
            });
        },

        _onReload: function () {
            var self = this;
            self.do_action('stock_barcode.stock_barcode_action_main_menu', {
                clear_breadcrumbs: true,
            });
        }
    });

    core.action_registry.add('product_lot_client_action', ProductLotClientAction);

});
