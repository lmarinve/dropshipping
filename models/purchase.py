# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import formatLang
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP
from odoo.addons import decimal_precision as dp
from odoo.addons.auth_signup.models.res_partner import SignupError, now

import hashlib
from Crypto import Random
from Crypto.Cipher import AES
import logging
_logger = logging.getLogger(__name__)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    user_id = fields.Many2one('res.users', string="Salesperson")
    vendor_del_date = fields.Date(string="Vendor Delivery Date")
    observ = fields.Text('Observation')
    sale_order = fields.Many2one('sale.order', string="Sale Order")

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            user_id = order.partner_id.user_id.id
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'user_id': user_id, 
            })

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        vendorId = self.order_id.partner_id.id
        vendorModel = env['product.supplierinfo']
        vendorObj = vendorModel.sudo().search([('name', '=', vendorId),('product_id', '=', product_id)])
        if vendorObj:
            self.vendor_code = vendorObj.product_code
        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.date_planned = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.price_unit = self.product_qty = 0.0
        self.product_uom = self.product_id.uom_po_id or self.product_id.uom_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context(
            lang=self.partner_id.lang,
            partner_id=self.partner_id.id,
        )
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        fpos = self.order_id.fiscal_position_id
        if self.env.uid == SUPERUSER_ID:
            company_id = self.env.user.company_id.id
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id.filtered(lambda r: r.company_id.id == company_id))
        else:
            self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        self._suggest_quantity()
        self._onchange_quantity()

        return result

    @api.multi
    def action_po_send(self):
        self.ensure_one()
        date_format = '%Y-%m-%d'
        delDate = self.date_planned
        mailTemplateModel = self.env['mail.template']
        irModelData = self.env['ir.model.data']
        templXmlId = irModelData.get_object_reference('dropship_portal', 'email_template_dropship_po')[1]
        vendorObj = self.partner_id
        user_id = self.partner_id.user_id.id
        x_id = str(self.id)
        expiration = now(days=+1)
        x_url = "3QI6I5o5fJTW2oCzivoK/"+ x_id + "/"
        x_notes = ""
        self.mapped('partner_id').signup_prepare(signup_type=x_url, expiration=expiration)
        redirectUrl = vendorObj.signup_url
        _logger.debug("*********** purchase.py action_po_send wurl: %r", redirectUrl)
        baseUrl = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        _logger.debug("*********** purchase.py action_po_send redirectUrl: %r", redirectUrl)
        if templXmlId and vendorObj:
            mailTmplObj = mailTemplateModel.browse(templXmlId)
            for vendor in vendorObj:
                ctx = {
                    'wkemail' : vendor.email,
                    'wkname' : vendor.name,
                    'wkDate' : delDate,
                    'lang' : vendor.lang,
                    'redirectUrl' : redirectUrl
                }
                mailTmplObj.with_context(**ctx).send_mail(self.id, force_send=True)
            trusted = vendor.trusted_vendor or False
            x_notes = "VALIDATED by " + vendor.name or ""
            if trusted:
                self.write({'state': 'purchase', 'user_id' : user_id, 'observ': x_notes})
            else:
                self.write({'state': "sent", 'user_id' : user_id, 'observ': x_notes})
        else:
            raise ValidationError(
            _('First add the Vendors'))

    @api.multi
    def print_quotation(self):
        self.env.ref('purchase.report_purchase_quotation').report_action(self)
        user_id = self.partner_id.user_id.id
        x_notes = ""
        self.write({'state': "sent", 'user_id' : user_id, 'observ': x_notes})

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        vendorModel = self.env['product.supplierinfo']
        for line in self:
            vendorId = line.order_id.partner_id.id
            product_id = line.product_id.id
            vendorObj = vendorModel.sudo().search([('name', '=', vendorId),('product_id', '=', product_id)])
            if vendorObj:
                vendor_code = vendorObj.product_code or ""

            taxes = line.taxes_id.compute_all(line.price_unit, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
                'vendor_code': vendor_code,
            })

    vendor_code = fields.Char(compute='_compute_amount', string='Vendor Id', store=True)
    sale_order = fields.Many2one(comodel_name='sale.order', string="Sale Order")
    sale_line = fields.Many2one('sale.order.line', string='soLine', index=True)

class ProcurementRule(models.Model):
    _inherit = 'procurement.rule'

    def _make_po_select_supplier(self, values, suppliers):
        """ Method intended to be overridden by customized modules to implement any logic in the
            selection of supplier.
        """
        print ("\n\n values-------", values)
        print ("\n\n rioute ids----",  values.get('route_ids'))
        if values.get('route_ids'):
            so = self.env['sale.order.line'].browse(values.get('sale_line_id'))
            supplier = so.vendor_id or suppliers[0]
            
            return supplier
        else:
            return super(ProcurementRule, self)._make_po_select_supplier(values, suppliers)

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        cache = {}
        suppliers = product_id.seller_ids\
            .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (not r.product_id or r.product_id == product_id))
        if not suppliers:
            msg = _('There is no vendor associated to the product %s. Please define a vendor for this product.') % (product_id.display_name,)
            raise UserError(msg)

        supplier = self._make_po_select_supplier(values, suppliers)
        partner = supplier.name
        domain = self._make_po_get_domain(values, partner)

        if domain in cache:
            po = cache[domain]
        else:
            po = self.env['purchase.order'].sudo().search([dom for dom in domain])
            po = po[0] if po else False
            cache[domain] = po
        if not po:
            vals = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
            po = self.env['purchase.order'].sudo().create(vals)
            cache[domain] = po
        elif not po.origin or origin not in po.origin.split(', '):
            if po.origin:
                if origin:
                    po.write({'origin': po.origin + ', ' + origin})
                else:
                    po.write({'origin': po.origin})
            else:
                po.write({'origin': origin})

        # Create Line
        po_line = False
        for line in po.order_line:
            if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                if line._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin, values):
                    vals = self._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
                    po_line = line.write(vals)
                    break
        if not po_line:
            vals = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, supplier)
            poLineObj = self.env['purchase.order.line'].sudo().create(vals)
            _logger.debug("********************* ProcurementRule values **********************: %r", values)
            _logger.debug("********************* end ProcurementRule values **********************")
            _logger.debug("********************* ProcurementRule vals **********************: %r", vals)
            _logger.debug("********************* end ProcurementRule vals **********************")
            _logger.debug("********************* ProcurementRule po **********************: %r", po)
            _logger.debug("********************* end ProcurementRule po **********************")
            _logger.debug("********************* ProcurementRule supplier **********************: %r", supplier)
            _logger.debug("********************* ProcurementRule partner **********************: %r", partner)
            partnerId = partner.id
            trusted = partner.trusted_vendor or False
            notes = "VALIDATED by " + partner.name or ""
            vendorId = supplier.id
            vendor_del_date = vals['date_planned']
            poOrder = po.id
            poLine = poLineObj.id
            sLine = vals['sale_line_id']
            saleLineObj = self.env['sale.order.line'].sudo().browse(sLine)
            if saleLineObj:
                sale_id = saleLineObj.order_id.id
                if sale_id:
                    poLineObj.write({'sale_order' : sale_id, 'sale_line' : sLine})
                    if trusted:
                        saleLineObj.write({'vendor_id': vendorId, 'assign_vendor': partnerId, 'po_order' : poOrder, 'po_line' : poLine, 'item_status' : 'OD'})
                    else:
                        saleLineObj.write({'vendor_id': vendorId, 'assign_vendor': partnerId, 'po_order' : poOrder, 'po_line' : poLine, 'item_status' : 'ND'})
        return True



    @api.multi
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, values, po, supplier):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_po_id)
        seller = product_id._select_seller(
            partner_id=supplier.name,
            quantity=procurement_uom_po_qty,
            date=po.date_order and po.date_order[:10],
            uom_id=product_id.uom_po_id)

        taxes = product_id.supplier_taxes_id
        fpos = po.fiscal_position_id
        taxes_id = fpos.map_tax(taxes) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == values['company_id'].id)

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price, product_id.supplier_taxes_id, taxes_id, values['company_id']) if seller else 0.0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id.compute(price_unit, po.currency_id)

        product_lang = product_id.with_context({
            'lang': supplier.name.lang,
            'partner_id': supplier.name.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        #date_planned = self.env['purchase.order.line']._get_date_planned(seller, po=po).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        sale_id = values.get('sale_id')
        sale_line_id = values.get('sale_line_id')
        date_planned = values.get('date_planned')
        return {
            'name': name,
            'product_qty': procurement_uom_po_qty,
            'product_id': product_id.id,
            'product_uom': product_id.uom_po_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'orderpoint_id': values.get('orderpoint_id', False) and values.get('orderpoint_id').id,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'order_id': po.id,
            'sale_id': sale_id,
            'sale_line_id': sale_line_id,
            'move_dest_ids': [(4, x.id) for x in values.get('move_dest_ids', [])],
        }




	