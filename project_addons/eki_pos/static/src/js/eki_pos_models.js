odoo.define('eki_pos.models', function(require) {
    "use strict";

    var models = require('point_of_sale.models');
    var utils = require('web.utils');
    var round_di = utils.round_decimals;
    var round_pr = utils.round_precision;

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
     * Extension of POS Product class
     */
    models.Product = models.Product.extend({

        /**
         * Copy of Orderline _compute_all function
         */
        _compute_all: function(tax, base_amount, quantity) {
            if (tax.amount_type === 'fixed') {
                var sign_base_amount = base_amount >= 0 ? 1 : -1;
                return (Math.abs(tax.amount) * sign_base_amount) * quantity;
            }
            if ((tax.amount_type === 'percent' && !tax.price_include) || (tax.amount_type === 'division' && tax.price_include)){
                return base_amount * tax.amount / 100;
            }
            if (tax.amount_type === 'percent' && tax.price_include){
                return base_amount - (base_amount / (1 + tax.amount / 100));
            }
            if (tax.amount_type === 'division' && !tax.price_include) {
                return base_amount / (1 - tax.amount / 100) - base_amount;
            }
            return false;
        },

        /**
         * Copy of Orderline compute_all function to allow Product price with tax computation
         */
        compute_price: function(taxes, price_unit, currency_rounding) {
            var self = this;
            var list_taxes = [];
            var currency_rounding_bak = currency_rounding;
            if (self.pos.company.tax_calculation_rounding_method == "round_globally"){
               currency_rounding = currency_rounding * 0.00001;
            }
            var total_excluded = round_pr(price_unit, currency_rounding);
            var total_included = total_excluded;
            var base = total_excluded;
            _(taxes).each(function(tax) {
                if (!tax){
                    return;
                }
                if (tax.amount_type === 'group'){
                    var ret = self.compute_price(tax.children_tax_ids, price_unit, 1, currency_rounding);
                    total_excluded = ret.total_excluded;
                    base = ret.total_excluded;
                    total_included = ret.total_included;
                    list_taxes = list_taxes.concat(ret.taxes);
                }
                else {
                    var tax_amount = self._compute_all(tax, base, 1);
                    tax_amount = round_pr(tax_amount, currency_rounding);

                    if (tax_amount){
                        if (tax.price_include) {
                            total_excluded -= tax_amount;
                            base -= tax_amount;
                        }
                        else {
                            total_included += tax_amount;
                        }
                        if (tax.include_base_amount) {
                            base += tax_amount;
                        }
                        var data = {
                            id: tax.id,
                            amount: tax_amount,
                            name: tax.name,
                        };
                        list_taxes.push(data);
                    }
                }
            });
            return round_pr(total_included, currency_rounding_bak);
        },

        /**
         * Function used to display price with tax on Pos ProductList widget
         * Called in Product extended QWeb template
         */
        get_display_price: function (pricelist, pos) {
            var self = this;
            self.pos = pos;
            var price_unit = self.get_price(pricelist, 1);

            var taxes_ids = self.taxes_id;
            var taxes =  self.pos.taxes;
            var product_taxes = [];

            _(taxes_ids).each(function(el){
                product_taxes.push(_.detect(taxes, function(t){
                    return t.id === el;
                }));
            });

            return self.compute_price(product_taxes, price_unit, self.pos.currency.rounding);
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