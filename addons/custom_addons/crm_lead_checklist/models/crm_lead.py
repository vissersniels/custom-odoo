from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ── Commercial Level ─────────────────────────────────────────────────────

    x_cl_end_customer = fields.Text(
        string='End Customer / Project Name / Application',
    )
    x_cl_known_partners = fields.Text(
        string='Known Partners / Who Needs the Counterparts',
    )
    x_cl_dmu = fields.Text(
        string='DMU – Who Makes the Decisions, on Which Criteria',
    )
    x_cl_location = fields.Text(
        string='Location – Samples / Mass Production',
    )
    x_cl_sop = fields.Text(
        string='SOP – Time Available Until Mass Production',
    )
    x_cl_qty_lifetime = fields.Text(
        string='QTY + Lifetime',
    )
    x_cl_milestones = fields.Text(
        string='Milestones',
    )
    x_cl_using_now = fields.Text(
        string='Current Situation – What Are They Using Now?',
    )
    x_cl_comparing_with = fields.Text(
        string='Current Situation – What Are They Comparing With?',
    )
    x_cl_status_company = fields.Text(
        string='Status of Company (Credit Check, Start-up Company, …)',
    )

    # ── Technical Level ───────────────────────────────────────────────────────

    x_tl_connector_types = fields.Text(
        string='Connector Types (Male/Female, Plug/Panel, Locking?, …)',
    )
    x_tl_mating_cycles = fields.Text(
        string='Mating Cycles',
    )
    x_tl_current_voltage = fields.Text(
        string='Required Current / Voltage (Continuous, Peak, … for Battery Charge & Discharge)',
    )
    x_tl_budget = fields.Text(
        string='Budget / Target Pricing (Tooling, Parts, …)',
    )
    x_tl_ip_level = fields.Text(
        string='IP Level',
    )
    x_tl_size_restrictions = fields.Text(
        string='Size Restrictions',
    )
    x_tl_material_restrictions = fields.Text(
        string='Material Restrictions',
    )
    x_tl_wiring_diagrams = fields.Text(
        string='Wiring Diagrams',
    )
    x_tl_cable_lengths = fields.Text(
        string='Cable Lengths',
    )
    x_tl_compliance = fields.Text(
        string='Compliance (Norms, EN, UL, …)',
    )
    x_tl_additional_notes = fields.Text(
        string='Additional Notes',
    )
