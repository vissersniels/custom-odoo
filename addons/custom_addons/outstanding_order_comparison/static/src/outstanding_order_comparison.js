/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, xml } from "@odoo/owl";

class OutstandingOrderComparison extends Component {
    static template = xml`<div class="o_view_controller"/>`;
}

registry.category("actions").add("outstanding_order_comparison.blank", OutstandingOrderComparison);
