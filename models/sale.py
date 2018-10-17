# -*- coding: utf-8 -*-
import uuid

from itertools import groupby
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from werkzeug.urls import url_encode

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

from odoo.tools.misc import formatLang

from odoo.addons import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _action_confirm(self):
        #super(SaleOrder, self)._action_confirm()
        for order in self.filtered(lambda order: order.partner_id not in order.message_partner_ids):
            order.message_subscribe([order.partner_id.id])
        self.write({
            'state': 'sale',
            'confirmation_date': fields.Datetime.now()
        })
        #if self.env.context.get('send_email'):
        #    self.force_quotation_send()

        for order in self:
            order.order_line._action_launch_procurement_rule()
        name = self.name
        poModel = self.env['purchase.order']
        pOrders = poModel.sudo().search([('origin', '=', name)])
        for orders in pOrders:
            _logger.debug("********************* dropship_portal\_action_confirm **********************: %r", orders)
            orders.action_po_send()

    @api.multi
    def action_quotation_send(self):
        self._action_confirm()
        self.write({'state': 'sent', 'confirmation_date': fields.Datetime.now()})
        return True

    @api.multi
    def action_done(self):
        for line in self.order_line:
            line.write({'item_status': 'FD'})
        self.write({'state': 'done'})
        return True

    @api.multi
    def action_confirm(self):
        #self._action_confirm()
        x_ready = True
        for line in self.order_line:
            if line.item_status != 'SH':
                x_ready = False
        if x_ready and self.env['ir.config_parameter'].sudo().get_param('sale.auto_done_setting'):
            self.action_done()
        return True

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_route = fields.Boolean('Is Route', default=False)
    vendor_id = fields.Many2one('product.supplierinfo', 'Vendor')
    assign_vendor = fields.Many2one('res.partner', string='Supplier', readonly=True)
    shipping_date = fields.Datetime(compute='_get_shipping_date', string='Shipping', index=True, readonly=True, store=True, help="Date on which the sales order is delivery.")
    init_qty = fields.Float(string='Ordered', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    po_order = fields.Many2one(comodel_name='purchase.order', string="pOrder", readonly=True)
    po_name = fields.Char('purchase.order', related='po_order.name', store=True)
    po_line = fields.Many2one(comodel_name='purchase.order.line', string="poLine", readonly=True)
    item_status = fields.Selection([
    ('BO','back ordered'),
    ('NM','needs manufacturing'),
    ('PM','pending manufacturing'),
    ('CM','committed for sale'),
    ('PI','picked'),
    ('PB','partial backorder'),
    ('PS','pending shipment'),
    ('SH','shipped'),
    ('QO','quotation'),
    ('SV','service item'),
    ('ND','not ordered'),
    ('OD','ordered'),
    ('FD','filled'), 
    ('HS','hold shipment'), 
    ('RT','return')], string='Item Status', readonly=True, store=True, default='QO')

    @api.multi
    @api.onchange('route_id')
    def _onchange_route_id(self):
        if self.route_id:
            self.is_route = True

    @api.depends('customer_lead')
    def _get_shipping_date(self):
        for line in self:
            line.shipping_date = datetime.today() + relativedelta(days=line.customer_lead or 1.0)

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name', 'price_unit', 'product_uom', 'tax_id']
        if values.get('order_id') and values.get('product_id') and any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.product_id_change()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        res['init_qty'] = values.get('product_uom_qty')
        _logger.debug("********************* dropship_portal\sale_order res **********************: %r", res)
        return res

    @api.multi
    def _prepare_procurement_values(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a procurement rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        self.ensure_one()
        date_planned = datetime.strptime(self.order_id.confirmation_date, DEFAULT_SERVER_DATETIME_FORMAT)\
            + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        route_id = self.route_id.id
        if not route_id or route_id == 5:
            _logger.debug("********** dropship_portal\sale_order _prepare_procurement_values NO ROUTE_Id ***********")
            self.item_status = "CM"
            self.route_id = 5
        values.update({
            'company_id': self.order_id.company_id,
            'group_id': group_id,
            'sale_line_id': self.id,
            'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'route_ids': self.route_id,
            'warehouse_id': self.order_id.warehouse_id or False,
            'partner_dest_id': self.order_id.partner_shipping_id
        })
        _logger.debug("********** dropship_portal\sale_order _prepare_procurement_values ***********")
        _logger.debug("********************* dropship_portal\sale_order _prepare_procurement_values: %r", values)
        _logger.debug("********** dropship_portal\end sale_order _prepare_procurement_values **********")
        return values


