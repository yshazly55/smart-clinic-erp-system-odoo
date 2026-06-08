from odoo import fields, models


class ClinicAppointmentType(models.Model):
    _name = "clinic.appointment.type"
    _description = "Clinic Appointment Type"

    name = fields.Char(required=True)

    specialization = fields.Selection(
        [
            ("general", "General"),
            ("cardiology", "Cardiology"),
            ("orthopedics", "Orthopedics"),
            ("pediatrics", "Pediatrics"),
            ("emergency", "Emergency"),
        ],
        string="Required Specialization",
        required=True,
        default="general",
    )

    duration_minutes = fields.Integer(string="Duration Minutes", default=30)

    supply_line_ids = fields.One2many(
        "clinic.appointment.supply.line",
        "appointment_type_id",
        string="Required Medical Supplies",
    )


class ClinicAppointmentSupplyLine(models.Model):
    _name = "clinic.appointment.supply.line"
    _description = "Supplies Required by Appointment Type"

    appointment_type_id = fields.Many2one(
        "clinic.appointment.type",
        required=True,
        ondelete="cascade",
    )
    supply_id = fields.Many2one("clinic.supply", required=True)
    quantity = fields.Float(required=True, default=1)
