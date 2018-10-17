odoo.define('purchase.reject', function (require) {
'use strict';

    require('web.dom_ready');
    var webPortal = require('portal.portal');
    var ajax = require('web.ajax');

    $('#wkreject').on("click", function(event){
        var rfqId = parseInt($('#rfqId').val());
        ajax.jsonRpc("/update/reject/", 'call', {'rfqId': rfqId})
        .then(function (vals){
            window.location.reload();
        });

    });

});
