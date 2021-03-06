# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import Warning
import random
from datetime import date, datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import barcode
try:
	from barcode.writer import ImageWriter
except ImportError:
	ImageWriter = None

import base64
import os


class pos_gift_coupon(models.Model):
	_name = 'pos.gift.coupon'
	
	
	def print_report_coupons(self):
		return self.env.ref('pos_orders_all.action_gift_coupons').report_action(self)


	@api.multi
	def existing_coupon(self,code):
		coupon_code_record =self.search([('c_barcode', '=',code)])
		if len(coupon_code_record) == 1:
			coupon_record = coupon_code_record[0]
			return True
		else:
			return False
		

	@api.multi
	def pos_screen_search_coupon(self, code):
		coupon_code_record = self.search([('id', '=', code)])
		if coupon_code_record:
			return [coupon_code_record.id,coupon_code_record.name,coupon_code_record.expiry_date,
					coupon_code_record.amount,coupon_code_record.issue_date,coupon_code_record.c_barcode,
					coupon_code_record.amount_type,coupon_code_record.c_barcode_img
					]

	@api.multi
	def search_coupon(self, code):
		coupon_code_record = self.search([('c_barcode', '=', code)])
		if coupon_code_record:
			return [coupon_code_record.id, coupon_code_record.amount,coupon_code_record.used, 
					coupon_code_record.coupon_count, coupon_code_record.coupon_apply_times, 
					coupon_code_record.expiry_date, coupon_code_record.partner_true,
					coupon_code_record.partner_id.id,coupon_code_record.amount_type,coupon_code_record.exp_dat_show,
					coupon_code_record.max_amount
					]


	@api.model
	def default_get(self, fields):
		pos_config_obj = self.env['pos.coupons.setting']
		if pos_config_obj.search_count([('active', '=',True)]) !=1 :
			raise Warning(_('Please configure gift coupons'))        

		
		rec = super(pos_gift_coupon, self).default_get(fields)
		config_obj = self.env['pos.coupons.setting']
		if config_obj.search_count([('active', '=',True)]) == 1:
			config_record = config_obj.search([('active', '=', True)])[0]
			if config_record:
				rec.update ({
					'amount': config_record.default_value ,
				})              
		return rec


	@api.one
	@api.constrains('issue_date','expiry_date')
	def _date_validate(self):

		if self.expiry_date and self.issue_date:
			if(self.expiry_date < self.issue_date):
				raise Warning(_( "Please Enter Valid Date."))

	@api.one
	@api.constrains('amount')
	def _check_amount(self):
		confing_obj = self.env['pos.coupons.setting']
		if confing_obj.search_count([('active', '=',True)]) == 1:
			config_record = confing_obj.search([('active', '=', True)])[0]
			if self.amount_type == 'fix':
				if self.amount < config_record.min_coupan_value or self.amount > config_record.max_coupan_value:
					raise Warning(_( "Amount is wrong"))


	@api.model
	def search_user(self):
		res_partner = self.env['res.partner'].search([])
		user_list = []
		for i in res_partner:
			user_list.append(i.name)
		return user_list

	@api.model
	def create_coupon_from_ui(self,data):
		
		coup_obj = self.env['pos.gift.coupon']
		amt_type = False

		if data['c_am_type'] == 'Fixed':
			amt_type = 'fix'
		else:
			amt_type = 'per'

		if data['c_expdt_box']:
			exp_check_box = True
			expiry_checked = data['c_exp_dt']
		else:
			exp_check_box = False
			expiry_checked = False

		if data['c_cust_box']:
			cust_check_box = True
			customer_select = self.partner_id.search([('name','=',data['c_customer'])]).id
		else:
			cust_check_box = False
			customer_select = False 

		vals = {
			'name':data['c_name'],
			'coupon_apply_times':data['c_limit'],
			'issue_date':data['c_issue_dt'],
			'amount':data['c_amount'],
			'amount_type':amt_type,
			'expiry_date':expiry_checked,
			'partner_id':customer_select,
			'exp_dat_show':exp_check_box,
			'partner_true':cust_check_box,
			'max_amount':data['coupon_max_amount'],
			'active': True,
			'user_id' :data['user_id']['id'],
		}
		res = coup_obj.sudo().create(vals)
		return res.id

	@api.model
	def create(self, vals):
		rec = super(pos_gift_coupon,self).create(vals)
		pos_config_obj = self.env['pos.coupons.setting']
		if pos_config_obj.search_count([('active', '=',True)]) !=1 :
			raise Warning(_('Please configure gift coupons'))
		else:
			code =(random.randrange(1111111111111,9999999999999))

			coupen_barcode = self.env['barcode.nomenclature'].sanitize_ean("%s" % (code))
			rec.write({'c_barcode':coupen_barcode})

			if ImageWriter != None:
				encode = barcode.get('ean13', coupen_barcode, writer=ImageWriter())
				filename = encode.save('ean13')
				file = open(filename, 'rb')
				jpgdata = file.read()
				imgdata = base64.encodestring(jpgdata)
				rec.write({'c_barcode_img':imgdata})
				os.remove(filename)

			if pos_config_obj.search_count([('active', '=',True)]) == 1:
				config_record = pos_config_obj.search([('active', '=', True)])[0]
				if config_record.default_availability != -1:
					if self.search_count([]) == config_record.default_availability:
						raise Warning(_('You can only create %d coupons  ') %  config_record.default_availability )                         
				config_record = config_record.search([('active', '=', True)])[0]
				if config_record:
					rec.update({'expiry_date':config_record.max_exp_date})

		return rec
		

		
	name  = fields.Char('Name')
	c_barcode = fields.Char(string="Coupen Barcode")
	c_barcode_img = fields.Binary('Coupen Barcode Image')
	user_id  =  fields.Many2one('res.users' ,'Created By',default  = lambda self: self.env.user)
	issue_date  =  fields.Datetime(default = datetime.now())
	exp_dat_show = fields.Boolean('Expiry Date')
	expiry_date  = fields.Datetime(string="Expiry Date")
	max_amount = fields.Float("Maximum amount")
	partner_true = fields.Boolean('Allow for Specific Customer')
	partner_id  =  fields.Many2one('res.partner')
	order_ids = fields.One2many('pos.order','coupon_id')
	active = fields.Boolean('Active',default=True)
	amount  =  fields.Float('Coupon Amount')
	amount_type = fields.Selection([('fix','Fixed'),('per','percentage(%)')],default='fix')
	description  =  fields.Text('Note')
	used = fields.Boolean('Used')   
	coupon_apply_times = fields.Integer('Coupon Code Apply Limit', default=1)
	coupon_count = fields.Integer('coupon count', default=1)
	coupon_desc = fields.Text('Discription')
	

	
	

