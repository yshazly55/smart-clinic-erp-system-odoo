from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    # We extend the normal Employees module.
    # Any employee marked with this checkbox can be selected as a clinic doctor.
    is_clinic_doctor = fields.Boolean(string="Clinic Doctor")

    clinic_specialization = fields.Selection(
        [
            ("general", "General"),
            ("cardiology", "Cardiology"),
            ("orthopedics", "Orthopedics"),
            ("pediatrics", "Pediatrics"),
            ("emergency", "Emergency"),
        ],
        string="Clinic Specialization",
    )

    clinic_active_ticket_count = fields.Integer(
        string="Active Clinic Tickets",
        compute="_compute_clinic_active_ticket_count",
    )

    def _compute_clinic_active_ticket_count(self):
        """Count how many active patients are assigned to each doctor."""
        Ticket = self.env["clinic.patient.ticket"]
        for employee in self:
            employee.clinic_active_ticket_count = Ticket.search_count(
                [
                    ("doctor_id", "=", employee.id),
                    ("state", "not in", ["done", "cancelled"]),
                ]
            )
