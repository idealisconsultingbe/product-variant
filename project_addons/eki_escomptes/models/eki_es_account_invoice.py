# -*- coding: utf-8 -*-
##############################################################################
#
# This module is developed by Idealis Consulting SPRL
# Copyright (C) 2019 Idealis Consulting SPRL (<http://idealisconsulting.com>).
# All Rights Reserved
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class EkiEscomptesAccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise UserError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line_ids.filtered(lambda line: line.account_id):
                raise UserError(_('Please add at least one invoice line.'))
            if inv.move_id:
                continue

            if not inv.date_invoice:
                inv.write({'date_invoice': fields.Date.context_today(self)})
            if not inv.date_due:
                inv.write({'date_due': inv.date_invoice})
            company_currency = inv.company_id.currency_id

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            iml = inv.invoice_line_move_line_get()
            iml += inv.tax_line_move_line_get()

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.compute_invoice_totals(company_currency, iml)

            name = inv.name or ''
            if inv.payment_term_id:
                totlines = inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
                discount_type = inv.type_pymnt_term_discount
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency._convert(t[1], inv.currency_id, inv.company_id,
                                                                    inv._get_currency_rate_date() or fields.Date.today())
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                # AMh Begin, Rework escomptes
                sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
                if discount_type in [1, 2] and inv.type in ['in_invoice', 'in_refund']:
                    iml_e, l_e = [], []
                    for l in iml:
                        if int(l['account_id']) == int(inv.account_id):
                            l_e.append(l)
                        else:
                            iml_e.append(l)
                    if l_e:
                        tot_lp = sum([l['price'] for l in l_e])
                        min_lp = max([l['price'] for l in l_e])
                        es_am = -sign * inv._get_amount_based_discount(self.amount_untaxed)[0]
                        for l in l_e:
                            if l['price'] == min_lp:
                                l['price'] = es_am
                                l['account_id'] = inv.property_account_discount_id.id
                                l['name'] = _('Discount')
                            else:
                                l['price'] = tot_lp - es_am

                    iml_e.extend(l_e)
                    iml = iml_e
                # AMH End
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'invoice_id': inv.id
                })
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
            line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
            line = inv.group_lines(iml, line)

            line = inv.finalize_invoice_move_lines(line)

            date = inv.date or inv.date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_ids': line,
                'journal_id': inv.journal_id.id,
                'date': date,
                'narration': inv.comment,
            }
            move = account_move.create(move_vals)
            # Pass invoice in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post(invoice=inv)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'date': date,
                'move_name': move.name,
            }
            inv.write(vals)
        return True

    @api.model
    def get_pay_term_lines(self):
        """ get payement term lines infos """
        res = {}
        for line in self.payment_term_id.line_ids:
            option = line.value
            if option not in res.keys():
                res[option] = []
            res[option].append({
                'option': line.option,
                'days': line.days,
                'value': line.value_amount,
            })
        return res

    @api.onchange("amount_untaxed", "payment_term_id")
    @api.depends("payment_term_id")
    def _compute_amount_discount(self):
        for o in self:
            o.amount_discount = o.amount_untaxed - self._get_amount_based_discount(self.amount_untaxed)[0]

    @api.multi
    @api.depends('payment_term_id')
    def _get_payement_term_discount_type(self):
        """Return escompte number based in payement term id"""
        for inv in self:
            if inv.payment_term_id:
                # begin AMH
                discount_type = inv.payment_term_id.discount_type
                inv.type_pymnt_term_discount = 3 if discount_type == 'discount_vat' else 2 if discount_type == 'discount' else 1

    @api.one
    def _get_amount_based_discount(self, value):
        # AMH begin
        if self.payment_term_id and self.type in ['in_invoice', 'in_refund']:
            prec_currency = self.currency_id or self.company_id.currency_id
            prec_currency = prec_currency.decimal_places
            try:
                ess = []
                for k, v in self.get_pay_term_lines().items():
                    if k == 'percent':
                        for term in v:
                            per = term['value']
                            return value - round(value * (per / 100.0),
                                                 prec_currency)  # just one (this is the escompte line)
            except Exception as e:
                print("LOG: Erreur apply discount", str(e))
                return value
        # AMH end
        return value

    def _get_tax_based_discount(self, value):
        """ apply escompte on htva amount """
        # AMH begin
        if self.payment_term_id and self.type in ['in_invoice', 'in_refund']:
            prec_currency = self.currency_id or self.company_id.currency_id
            prec_currency = prec_currency.decimal_places
            if self.type_pymnt_term_discount == 2 or self.type_pymnt_term_discount == 3:
                try:
                    ess = []
                    for k, v in self.get_pay_term_lines().items():
                        if k == 'percent':
                            for term in v:
                                per = term['value']
                                return round(value * (per / 100.0), prec_currency)  # just one (this is the escompte line)
                except Exception as e:
                    print("LOG: Erreur apply discount on tax", str(e))
                    return value
        # AMH end
        return value

    def _compute_amount(self):
        super(EkiEscomptesAccountInvoice, self)._compute_amount()
        # AMH begin, rework Escompte
        self.amount_discount = self.amount_untaxed - self._get_amount_based_discount(self.amount_untaxed)[0]
        if self.type_pymnt_term_discount == 2:
            self.amount_untaxed = self.amount_discount
        # AMH end

    def _prepare_tax_line_vals(self, line, tax):
        vals = super(EkiEscomptesAccountInvoice, self)._prepare_tax_line_vals(line ,tax)
        # Amh begin
        vals['amount'] = self._get_tax_based_discount(vals['amount'])
        vals['base'] = self._get_tax_based_discount(vals['base'])
        # Amh end
        return vals

    @api.onchange('payment_term_id')
    def _onchange_payment_term(self):
        if not self.payment_term_id and self.partner_id:
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id
            self._onchange_invoice_line_ids()
        else:
            self._onchange_invoice_line_ids()

    type_pymnt_term_discount = fields.Integer(string="Discount type", default=1, compute=_get_payement_term_discount_type)
    amount_discount = fields.Float(string="Untaxed Amount (Disc)", default=0.0, compute=_compute_amount_discount)
    property_account_discount_id = fields.Many2one('account.account', company_dependent=True, string="Account Discount", help="This account will be used for discount", required=True)


class EkiEscomptesAccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    _description = "Payment Terms"

    discount_type = fields.Selection([('total', 'VAT based on total amount'), ('discount', 'Discount htva + VAT based on the amount discounted'), ('discount_vat', 'VAT based on the amount discounted')], string="Type of discount", default="total")
