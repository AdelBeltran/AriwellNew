// © 2015-2018 Eneldo Serrata <eneldo@marcos.do>
// © 2017-2018 Gustavo Valverde <gustavo@iterativo.do>
// © 2018 Francisco Peñaló <frankpenalo24@gmail.com>
// © 2018 Kevin Jiménez <kevinjimenezlorenzo@gmail.com>

// This file is part of NCF Manager.

// NCF Manager is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// NCF Manager is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.

// You should have received a copy of the GNU General Public License
// along with NCF Manager.  If not, see <https://www.gnu.org/licenses/>.

odoo.define("l10n_do_pos.models", function (require) {
  "use strict";

  var models = require("point_of_sale.models");
  var rpc = require("web.rpc");

  models.load_fields("res.partner", ["l10n_do_dgii_tax_payer_type"]);
  models.load_fields("account.journal", ["payment_form"]);
  models.load_fields("pos.config",
    ["default_partner_id", "print_pdf", "ncf_control", "order_search_criteria", "seller_and_cashier_ticket"]
  );
  models.load_fields("res.company", ["street", "street2", "city", "state_id", "country_id", "zip"]);
  models.load_models([{
    model: "pos.order",
    fields: ["id", "name", "ncf", "date_order", "partner_id", "lines", "pos_reference", "account_move",
      "amount_total", "return_order_id", "is_return_order",
      "return_status", "sale_fiscal_type", "ncf_invoice_related", "account_move"],
    domain: function (self) {
      var domain_list = [];

      if (self.config.order_loading_options === "n_days") {
        var today = new Date();
        var validation_date = new Date(today);
        validation_date.setDate(today.getDate() - self.config.number_of_days);

        domain_list = [
          ["account_move.invoice_date", ">", validation_date.toISOString()],
          ["state", "not in", ["draft", "cancel"]],
          ["config_id", "=", self.config.id],
        ];
      } else {
        domain_list = [
          ["session_id", "=", self.pos_session.id],
          ["state", "not in", ["draft", "cancel"]],
        ];
      }
      domain_list.push(["is_return_order", "=", false]);
      return domain_list;
    },
    loaded: function (self, orders) {
      self.db.pos_all_orders = orders || [];
      self.db.order_by_id = {};
      orders.forEach(function (order) {
        order.l10n_latam_document_number = order.ncf;
        order.account_move = [order.account_move[0], order.ncf];
        self.db.order_by_id[order.id] = order;
      });
    },
  }, {
    model: "account.move",
    fields: ["l10n_latam_document_number", "ref"],

    domain: function (self) {
      var invoice_ids = self.db.pos_all_orders.map(function (order) {
        return order.account_move[0];
      });

      return [["id", "in", invoice_ids]];
    },
    loaded: function (self, invoices) {
      var invoice_by_id = {};

      invoices.forEach(function (invoice) {
        invoice_by_id[invoice.id] = invoice;
      });

      self.db.pos_all_orders.forEach(function (order, ix) {
        var account_move = invoice_by_id[order.account_move[0]];
        var number = account_move && account_move.ref;

        self.db.pos_all_orders[ix].number = number;
        self.db.order_by_id[order.id].number = number;
      });
    },
  }, {
    model: "account.move",
    fields: ["l10n_latam_document_number", "partner_id"],
    domain: function (self) {
      var today = new Date();
      var validation_date = new Date(today);
      validation_date.setDate(today.getDate() - self.config.credit_notes_number_of_days);

      return [
        ["move_type", "=", "out_refund"], ["state", "!=", "paid"],
        ["invoice_date", ">", validation_date.toISOString()],
      ];
    },
    loaded: function (self, invoices) {
      var credit_note_by_id = {};
      var credit_notes_by_partner_id = {};
      var partner_id = false;

      _.each(invoices, function (invoice) {
        partner_id = invoice.partner_id[0];
        invoice.partner_id = self.db.get_partner_by_id(partner_id);

        credit_note_by_id[invoice.id] = invoice;

        credit_notes_by_partner_id[partner_id] = credit_notes_by_partner_id[partner_id] || [];
        credit_notes_by_partner_id[partner_id].push(invoice);
      });

      self.db.credit_note_by_id = credit_note_by_id;
      self.db.credit_notes_by_partner_id = credit_notes_by_partner_id;
    },
  }, {
    model: "pos.order.line",
    fields: ["product_id", "order_id", "qty", "discount", "price_unit", "price_subtotal_incl",
      "price_subtotal", "line_qty_returned"],
    domain: function (self) {
      var orders = self.db.pos_all_orders;
      var order_lines = [];

      for (var i in orders) {
        order_lines = order_lines.concat(orders[i].lines);
      }

      return [
        ["id", "in", order_lines],
      ];
    },
    loaded: function (self, order_lines) {
      self.db.pos_all_order_lines = order_lines || [];
      self.db.line_by_id = {};
      order_lines.forEach(function (line) {
        self.db.line_by_id[line.id] = line;
      });
    },
  }], {
    "after": "product.product",
  });
  // models.load_models([{
  //     label: "Custom Account Journal",
  //     loaded: function (self, tmp) {
  //         // var cashregister_credit_note = $.extend({}, self.cashregisters[0]);
  //         //
  //         // for (var n in self.cashregisters) {
  //         //     if (self.cashregisters[n].journal.type.toLowerCase() === "cash") {
  //         //         cashregister_credit_note = $.extend({}, self.cashregisters[n]);
  //         //         break;
  //         //     }
  //         // }
  //         cashregister_credit_note = $.extend(cashregister_credit_note, {
  //             id: 10001,
  //             journal_id: [10001, 'Nota de Credito'],
  //             journal: {type: 'cash', id: 10001, sequence: 10001},
  //             css_class: 'altlight',
  //             show_popup: true,
  //             popup_name: 'textinput',
  //             popup_options: {},
  //         });
  //
  //         // Creamos una forma de pago especial para la Nota de Credito
  //         self.cashregisters.push(cashregister_credit_note);
  //         self.cashregisters_by_id[cashregister_credit_note.id] = cashregister_credit_note;
  //     },
  // }], {
  //     'after': 'account.journal',
  // });
  models.load_models([{
    label: "Search Criteria",
    model: "pos.search_criteria",
    fields: ["id", "name", "criteria"],
    loaded: function (self, criterias) {
      _.each(self.config.order_search_criteria, function (criteria_id, index) {
        self.config.order_search_criteria[index] = _.findWhere(criterias, {id: criteria_id}).criteria;
      });
    },
  }], {"after": "pos.config"});

  var _super_posmodel = models.PosModel.prototype;
  models.PosModel = models.PosModel.extend({
    initialize: function (session, attributes) {
      this.invoices = [];
      this.sale_fiscal_type_selection = []; // This list define sale_fiscal_type on pos
      this.sale_fiscal_type_default_id = "final"; // This define the default id of sale_fiscal_type
      this.sale_fiscal_type = []; // This list define sale_fiscal_type on pos
      this.sale_fiscal_type_by_id = {}; // This object define sale_fiscal_type on pos
      this.sale_fiscal_type_vat = []; // This list define relation between sale_fiscal_type and vat on pos

      _super_posmodel.initialize.call(this, session, attributes);
    },
    load_server_data: function () {
      this.load_sale_fiscal_types();
      return _super_posmodel.load_server_data.call(this);
    },
    load_sale_fiscal_types: function () {
      var self = this;

      rpc.query({
        model: "res.partner",
        method: "get_sale_fiscal_type_selection",
        args: [],
      }, {}).then(function (result) {
        self.sale_fiscal_type_selection = result.l10n_latam_document_type_id;
        // self.sale_fiscal_type_vat = result.sale_fiscal_type_vat;
        self.sale_fiscal_type_list = result.sale_fiscal_type_list;
        self.sale_fiscal_type_by_id = {};
        for (var n in result.sale_fiscal_type_list) {
          var item = result.sale_fiscal_type_list[n];
          self.sale_fiscal_type_by_id[item.l10n_do_ncf_type] = item;
        }
      });
    },

    /**
     * Return a object with the sale fiscal type
     *
     * @param {String} sale_fiscal_type_id - The value of sale fiscal type
     * @returns {Object} Return a object with the sale fiscal type filtered by the id.
     * If the id is invalid then return a object with the default sale fiscal type
     */
    get_sale_fiscal_type: function () {
      var currentOrder = this.get_order();
      return {ncf: currentOrder.ncf, sale_fiscal_type: currentOrder.sale_fiscal_type}
    },

    getDatetime: function () {
      var date = new Date(),
        time = new Date(),
        timezone = "es-ES",
        dateOptions = {day: "2-digit", month: "2-digit", year: "numeric"},
        timeOptions = {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true
        };

      return {
        date: date.toLocaleDateString(timezone, dateOptions),
        time: time.toLocaleTimeString(timezone, timeOptions),
        datetime: date.toLocaleDateString(timezone, _.extend(dateOptions, timeOptions)),
      };
    },
    set_order: function (order) {
      _super_posmodel.set_order.call(this, order);

      if (order && order.is_return_order === true) {
        this.gui.show_screen("payment");
      }
    },

    /**
     * Envia un arreglo con las ordenes al servidor para generar las facturas
     * y luego de creadas facturas para las que sean de nota de credito actualizamos
     * la BD offline con los cambios
     * @param {Object} orders - Objeto con la lista de ordenes
     * @param {Object} options - Objeto con los configuracion opcional
     * @returns {Promise} Promise con la lista de ids generados en el servidor
     * @private
     */
    _save_to_server: function (orders, options) {
        var self = this;
      var server = _super_posmodel._save_to_server.call(this, orders, options);
      server.then(function (result){
        var currentOrder = self.get_order();
        if(result.length > 0){
          if(result[0].pos_reference == currentOrder.name){
            currentOrder.ncf = result[0].ncf;
            currentOrder.sale_fiscal_type = result[0].sale_fiscal_type;
          }
        }
      });
      return server;
    },
    get_orders_from_server: function () {
      var self = this;
      var max_invoice_id = Math.max(..._.map(this.db.pos_all_orders, function (o) {
        return o.account_move[0];
      }), 0);

      var kwargs = {
        invoice_id: max_invoice_id,
      };
      var loading_type = posmodel.config.order_loading_options;

      if (loading_type === "n_days") {
        kwargs.day_limit = this.config.number_of_days || 0;
        kwargs.config_id = this.config.id;
      } else if (loading_type === "current_session") {
        kwargs.session_id = posmodel.pos_session.id;
      }

      rpc.query({
        model: "pos.order",
        method: "order_search_from_ui",
        args: [],
        kwargs: kwargs,
      }, {}).then(function (result) {
        var orders = result && result.orders || [];
        var orderlines = result && result.orderlines || [];

        orders.forEach(function (order) {
          var obj = self.db.order_by_id[order.id];

          if (!obj) {
            self.db.pos_all_orders.unshift(order);
          }
          self.db.order_by_id[order.id] = order;
        });
        self.db.pos_all_order_lines.concat(orderlines);
        orderlines.forEach(function (line) {
          self.db.line_by_id[line.id] = line;
        });

        self.gui.screen_instances.invoiceslist.render_list(
          self.db.pos_all_orders);

      });
    },

  });

  var _super_order = models.Order.prototype;
  models.Order = models.Order.extend({
    get_ncf: function(currentOrder){
      rpc.query({
        model: "pos.order",
        method: "get_from_ui",
        args: [currentOrder]
      },{
        timeout: 50000,
      }).then(function(result){
        console.log(result);
        return result;
      });


    },
    initialize: function (attributes, options) {
      this.return_status = "-";
      this.is_return_order = false;
      this.return_order_id = false;
      this.sale_fiscal_type = false;
      this.orderlineList = [];
      this.ncf = false;
      _super_order.initialize.call(this, attributes, options);

      this.ncf_control = this.pos.config.ncf_control;

      if (this.pos.config.module_account && !this.get_client()) {
        var pos_default_partner = this.pos.config.default_partner_id;

        this.to_invoice = true;
        if (pos_default_partner) {
          var client = this.pos.db.get_partner_by_id(pos_default_partner[0]);

          if (client) {
            this.set_client(client);
          }
        }
      }
    },
    init_from_JSON: function (json) {
      var self = this;

      _super_order.init_from_JSON.call(this, json);
      this.return_status = json.return_status;
      this.is_return_order = json.is_return_order;
      this.return_order_id = json.return_order_id;
      this.sale_fiscal_type = json.sale_fiscal_type;
      this.amount_total = json.amount_total;
      this.to_invoice = json.to_invoice;
      this.ncf = json.ncf;
      this.ncf_control = json.ncf_control;
      if (this.orderlines && $.isArray(this.orderlines.models)) {
        this.orderlines.models.forEach(function (line) {
          var productDefCode = line.product.default_code;

          self.orderlineList.push(
            {
              line_id: line.id,
              product_id: line.product.id,
              product_name: (productDefCode && "[" + productDefCode + "] " || "") + line.product.display_name,
              quantity: line.quantity,
              price: line.price,
            });
        });
      }
    },
    export_as_JSON: function () {
      var json = _super_order.export_as_JSON.call(this);

      $.extend(json, {
        return_status: this.return_status,
        is_return_order: this.is_return_order,
        return_order_id: this.return_order_id,
        sale_fiscal_type: this.sale_fiscal_type,
        amount_total: parseFloat(json.amount_total || 0),
        to_invoice: this.to_invoice,
        ncf: this.ncf,
        ncf_control: this.ncf_control,
      });
      return json;
    },
    export_for_printing: function(){
      var json = _super_order.export_for_printing.call(this);
      // while(json['ncf'] == undefined || json['ncf'] == false){
      //   json['ncf'] = this.get_ncf(json.name);
      //   console.log(this.get_ncf(json.name));
      //   console.log(json);
      //   console.log('===============');
      // }

      return json;
    },
  });

  var _super_orderline = models.Orderline.prototype;
  models.Orderline = models.Orderline.extend({
    initialize: function (attr, options) {
      this.line_qty_returned = 0;
      this.original_line_id = null;
      _super_orderline.initialize.call(this, attr, options);
    },
    init_from_JSON: function (json) {
      _super_orderline.init_from_JSON.call(this, json);
      this.line_qty_returned = json.line_qty_returned;
      this.original_line_id = json.original_line_id;
    },
    export_as_JSON: function () {
      var json = _super_orderline.export_as_JSON.call(this);

      $.extend(json, {
        line_qty_returned: this.line_qty_returned,
        original_line_id: this.original_line_id,
      });
      return json;
    },
  });

  var super_paymentline = models.Paymentline.prototype;
  models.Paymentline = models.Paymentline.extend({
    initialize: function (attr, options) {
      this.credit_note_id = null;
      this.note = "";
      super_paymentline.initialize.call(this, attr, options);
    },
    init_from_JSON: function (json) {
      super_paymentline.init_from_JSON.call(this, json);
      this.credit_note_id = json.credit_note_id;
      this.note = json.note;
    },
    export_as_JSON: function () {
      var json = super_paymentline.export_as_JSON.call(this);

      $.extend(json, {
        credit_note_id: this.credit_note_id,
        note: this.note,
        // payment_reference: this.cashregister.payment_reference,
      });
      return json;
    },
  });
});
