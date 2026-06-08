from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ClinicPatientTicket(models.Model):
    _name = "clinic.patient.ticket"
    _description = "Clinic Patient Intake Ticket"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "score desc, arrival_time asc"

    name = fields.Char(string="Ticket Reference", default="New", copy=False, readonly=True)
    patient_name = fields.Char(required=True, tracking=True)
    age = fields.Integer()
    symptoms = fields.Text()

    priority = fields.Selection(
        [
            ("emergency", "Emergency"),
            ("urgent", "Urgent"),
            ("routine", "Routine"),
        ],
        required=True,
        default="routine",
        tracking=True,
    )

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

    score = fields.Integer(compute="_compute_score", store=True)
    arrival_time = fields.Datetime(default=fields.Datetime.now, required=True)

    doctor_id = fields.Many2one(
        "hr.employee",
        string="Assigned Doctor",
        domain="[('is_clinic_doctor', '=', True)]",
        tracking=True,
    )

    appointment_type_id = fields.Many2one("clinic.appointment.type", string="Appointment Type")
    appointment_id = fields.Many2one("clinic.appointment", string="Appointment", readonly=True)

    state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("assigned", "Assigned"),
            ("appointment", "Appointment Created"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="waiting",
        tracking=True,
    )

    waiting_minutes = fields.Integer(compute="_compute_waiting_minutes")
    overdue = fields.Boolean(compute="_compute_overdue")

    @api.model_create_multi
    def create(self, vals_list):
        """Create a simple ticket number without needing sequence XML."""
        records = super().create(vals_list)
        for record in records:
            if record.name == "New":
                record.name = f"PT-{record.id:05d}"
        return records

    @api.depends("priority")
    def _compute_score(self):
        """Priority scoring algorithm.

        Higher score appears first in the intake queue.
        """
        score_map = {
            "emergency": 100,
            "urgent": 60,
            "routine": 20,
        }
        for ticket in self:
            ticket.score = score_map.get(ticket.priority, 0)

    def _compute_waiting_minutes(self):
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.arrival_time:
                difference = now - ticket.arrival_time
                ticket.waiting_minutes = int(difference.total_seconds() / 60)
            else:
                ticket.waiting_minutes = 0

    def _compute_overdue(self):
        """Flag patients who waited too long.

        Emergency: 5 min, Urgent: 15 min, Routine: 30 min.
        """
        limit_map = {
            "emergency": 5,
            "urgent": 15,
            "routine": 30,
        }
        for ticket in self:
            limit = limit_map.get(ticket.priority, 30)
            ticket.overdue = ticket.state not in ["done", "cancelled"] and ticket.waiting_minutes > limit

    def action_auto_assign_doctor(self):
        """Assign the patient to the least-busy matching doctor."""
        Appointment = self.env["clinic.appointment"]
        Ticket = self.env["clinic.patient.ticket"]

        for ticket in self:
            doctors = self.env["hr.employee"].search(
                [
                    ("is_clinic_doctor", "=", True),
                    ("clinic_specialization", "=", ticket.specialization),
                ]
            )

            # Fallback: if no exact specialization exists, use any clinic doctor.
            if not doctors:
                doctors = self.env["hr.employee"].search([("is_clinic_doctor", "=", True)])

            if not doctors:
                raise ValidationError("No clinic doctors found. Create an Employee and mark them as Clinic Doctor first.")

            def doctor_load(doctor):
                active_tickets = Ticket.search_count(
                    [
                        ("doctor_id", "=", doctor.id),
                        ("state", "not in", ["done", "cancelled"]),
                    ]
                )
                scheduled_appointments = Appointment.search_count(
                    [
                        ("doctor_id", "=", doctor.id),
                        ("state", "=", "scheduled"),
                    ]
                )
                return active_tickets + scheduled_appointments

            selected_doctor = min(doctors, key=doctor_load)
            ticket.doctor_id = selected_doctor.id
            ticket.state = "assigned"
            ticket.message_post(body=f"Auto-assigned to {selected_doctor.name} based on specialization and workload.")

    def action_create_appointment(self):
        """Create an appointment now using the assigned doctor and appointment type."""
        for ticket in self:
            if not ticket.doctor_id:
                raise ValidationError("Assign a doctor before creating the appointment.")
            if not ticket.appointment_type_id:
                raise ValidationError("Choose an appointment type before creating the appointment.")

            start_time = fields.Datetime.now()
            end_time = start_time + timedelta(minutes=ticket.appointment_type_id.duration_minutes or 30)

            appointment = self.env["clinic.appointment"].create(
                {
                    "patient_ticket_id": ticket.id,
                    "doctor_id": ticket.doctor_id.id,
                    "appointment_type_id": ticket.appointment_type_id.id,
                    "start_datetime": start_time,
                    "end_datetime": end_time,
                }
            )

            ticket.appointment_id = appointment.id
            ticket.state = "appointment"
            ticket.message_post(body=f"Appointment created with {ticket.doctor_id.name}.")

    def action_mark_done(self):
        for ticket in self:
            if ticket.appointment_id and ticket.appointment_id.state != "done":
                ticket.appointment_id.action_mark_done()
            ticket.state = "done"

    def action_cancel(self):
        for ticket in self:
            ticket.state = "cancelled"
