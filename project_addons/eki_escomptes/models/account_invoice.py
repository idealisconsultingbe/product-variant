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
                totlines = \
                inv.payment_term_id.with_context(currency_id=company_currency.id).compute(total, inv.date_invoice)[0]
                res_amount_currency = total_currency
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

    def _get_payement_term_escompte_type(self):
        """Return escompte number based in payement term id"""
        for inv in self:
            if inv.payment_term_id:
                # begin AMH
                act_htva = inv.payment_term_id.act_htva
                act_tva = inv.payment_term_id.act_tva
                inv.type_pymnt_term_escompte = 3 if (act_htva and act_tva) else 2 if act_tva else 1 if act_htva else 0  # escompte 1,2 or 3

    @api.one
    def _get_amount_based_escompte(self, value):
        """ apply escompte on amount"""
        currency = self.currency_id or None
        # AMH begin
        if self.payment_term_id and self.type in ['in_invoice', 'in_refund']:
            prec_currency = self.currency_id or self.company_id.currency_id
            prec_currency = prec_currency.decimal_places
            act_htva = self.payment_term_id.act_htva
            act_tva = self.payment_term_id.act_tva
            if self.payment_term_id and (self.payment_term_id.act_htva
                                         or self.payment_term_id.act_tva):
                try:
                    ess = []
                    for k, v in self.get_pay_term_lines().items():
                        if k == 'percent':
                            for term in v:
                                per = term['value']
                                return value - round(value * (per / 100.0),
                                                     prec_currency)  # just one (this is the escompte line)
                except Exception as e:
                    print("LOG: Erreur apply escompte", e.message)
                    return value
        # AMH end
        return value

    def _get_tax_based_escompte(self, value):
        """ apply escompte on htva amount """
        currency = self.currency_id or None
        # AMH begin
        if self.payment_term_id and self.type in ['in_invoice', 'in_refund']:
            prec_currency = self.currency_id or self.company_id.currency_id
            prec_currency = prec_currency.decimal_places
            act_htva = self.payment_term_id.act_htva
            act_tva = self.payment_term_id.act_tva
            if self.payment_term_id and self.payment_term_id.act_tva:
                try:
                    ess = []
                    for k, v in self.get_pay_term_lines().items():
                        if k == 'percent':
                            for term in v:
                                per = term['value']
                                return round(value * (per / 100.0), prec_currency)  # just one (this is the escompte line)
                except Exception as e:
                    print("LOG: Erreur apply escompte on tax", e.message)
                    return value
        # AMH end
        return value


class EkiEscomptesAccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    _description = "Payment Terms"

    act_tva = fields.Selection([('total', 'VAT based on total amount'), ('discount', 'VAT based on the amount discounted')], string="VAT based on?", default="total")
