odoo.define('eki_pos.models', function(require) {
    "use strict";

    var models = require('point_of_sale.models');

    /**
     * Extension of PosModel class
     */
    var _super_pos_model = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        /**
         * Override initialize function to retrieve eki_return field
         * from product.product records
         * @param session
         * @param attributes
         */
        initialize: function (session, attributes) {

            var product_model = _.find(this.models, function (model) {
                return model.model === 'product.product';
            });
            product_model.fields.push('eki_return', 'eki_is_return');
            _super_pos_model.initialize.apply(this, arguments);
        },
    });

    /**
     * Extension of POS Order Line
     */
    var _super_pos_order_line = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({

        /**
         * Override set_quantity function to synchronize eki_return order line quantity
         * @param quantity
         * @param keep_price
         */
        set_quantity: function (quantity, keep_price) {
            var self = this;
            _super_pos_order_line.set_quantity.apply(this, arguments);
            if (self.product.eki_return) {
                this.sync_return_qty();
            }
        },

        can_be_merged_with: function (line) {
            if (this.is_return_line) {
                return false;
            }
            else return _super_pos_order_line.can_be_merged_with.apply(this, arguments);
        },

        /**
         * Synchronize return product quantity order line
         */
        sync_return_qty: function () {
            var self = this;
            // Get order line with eki_return product
            var lines_with_return = self.order.orderlines.models.filter(line => {
                return line.product.eki_return;
            });

            // foreach orderline
            // compute total eki_return product qty and update appropriate line qty
            var return_product_done = [];
            _.each(lines_with_return, function (line, index, lst) {

                var eki_return_id = line.product.eki_return[0];

                // Check if return product line has already been processed
                if (!_.contains(return_product_done, eki_return_id)) {

                    // Get line with same return product
                    var same_return_line = lst.filter(line => {
                        return line.product.eki_return[0] === eki_return_id;
                    });
                    // Compute total qty from same_return_line
                    var sum_qty = _.reduce(same_return_line, function (sum, line) { return sum + line.get_quantity(); }, 0);

                    // Find eki_return order line and update quantity
                    var eki_return_line = _.find(self.order.orderlines.models, function(line) { return line.product.id === eki_return_id && line.is_return_line; });
                    if (eki_return_line) {
                        _super_pos_order_line.set_quantity.apply(eki_return_line, [sum_qty]);
                    }
                    // Push eki_return product id to processed stack to avoid unnecessary computation
                    return_product_done.push(eki_return_id);
                }
            });
        },

        /**
         * Override default get_display_price to always display VAT included price
         * @returns {*}
         */
        get_display_price: function(){
            return this.get_price_with_tax();
        },
    });

    /**
     * Extension of POS Order class
     */
    var _super_pos_order = models.Order.prototype;
    models.Order = models.Order.extend({

        /**
         * Override add_product function to add return product
         * automatically if eki_return field is set
         * @param product: product object
         * @param options: adding options
         */
        add_product: function (product, options) {
            _super_pos_order.add_product.apply(this, arguments);
            var line = this.get_last_orderline();

            var eki_return = line.product.eki_return;
            if (eki_return) {
                var eki_return_id = eki_return[0];
                // If a line already have eki_return product update it
                // otherwise add it to the order
                var eki_return_line = _.find(this.orderlines.models, function(line) { return line.product.id === eki_return_id && line.is_return_line; });
                if (eki_return_line) {
                    eki_return_line.sync_return_qty();
                }
                else {
                    options = options || {};
                    options.merge = false;
                    _super_pos_order.add_product.apply(this, [this.pos.db.get_product_by_id(eki_return_id), options]);
                    var return_line = this.get_last_orderline();
                    return_line.is_return_line = true;
                }
            }
            this.select_orderline(line);
        },
    });
});