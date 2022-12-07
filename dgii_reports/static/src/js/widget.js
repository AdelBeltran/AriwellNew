odoo.define('dgii_report.dgii_report_widget', function (require) {
    "use strict";

    var basicFields = require('web.basic_fields');
    var field_registry = require('web.field_registry');

   
    var UrlDgiiReportsWidget = basicFields.UrlWidget.extend({

        _renderReadonly: function () {
            
            this.$el.html(`<a  target="_blank" 
                           class="o_form_uri o_text_overflow" 
                           href="dgii_reports/${this.value}">
                           ${this.value} </a>`);
                           

            //this method open up a <div> instead of a <a> tag

            // this.$el.$("a").text(this.attrs.text || this.value) 
                
            //     .addClass('o_form_uri o_text_overflow')
            //     .attr('target', '_blank')
            //     .attr('href', "dgii_reports/"+this.value);

                
        },
    });
    field_registry.add('dgii_reports_url', UrlDgiiReportsWidget);

    
    return UrlDgiiReportsWidget;


});