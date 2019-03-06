# Copyright 2016 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


def set_sale_price_on_variant(cr, registry, template_id=None):
    sql = """
        UPDATE product_product pp
        SET fix_price = pt.list_price
        FROM product_template pt
        WHERE %s;
    """ % ('pt.id = pp.product_tmpl_id' +
           (template_id and ' AND pt.id = %s' % template_id or ''))
    cr.execute(sql)
