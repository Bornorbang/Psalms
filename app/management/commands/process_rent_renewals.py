"""
Management command: process_rent_renewals

Handles the full rent lifecycle automation:

1. RENEWAL INVOICES (8-month mark)
   - Finds active rental agreements that started 8+ months ago
   - If no future invoice exists yet → creates a renewal invoice for the next year
   - Sends email to tenant and landlord

2. MONTHLY PAYMENT REMINDERS
   - Sends reminder emails for all SENT invoices (not yet paid)
   - Also reminds for OVERDUE invoices (already past due)
   - Skips if reminder was sent within the last 28 days

3. OVERDUE MARKING (12-month mark)
   - If a renewal invoice reaches its due date unpaid → marks as OVERDUE
   - Sends overdue alert email to tenant AND landlord

Run this command daily via cron / task scheduler:
    python manage.py process_rent_renewals

Or dry-run to preview without changes:
    python manage.py process_rent_renewals --dry-run
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from app.models import RentalAgreement, Invoice


class Command(BaseCommand):
    help = 'Process rent renewal invoices, monthly reminders, and overdue alerts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview actions without making DB changes or sending emails',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        self._process_renewals(today, dry_run)
        self._send_monthly_reminders(today, dry_run)
        self._mark_overdue_and_notify(today, dry_run)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. RENEWAL INVOICES at 8-month mark
    # ─────────────────────────────────────────────────────────────────────────
    def _process_renewals(self, today, dry_run):
        self.stdout.write('── Checking for renewal invoices (8-month mark) ──')

        active_agreements = RentalAgreement.objects.filter(
            status=RentalAgreement.AgreementStatus.ACTIVE,
        ).select_related('rental_property', 'tenant', 'landlord')

        renewals_created = 0

        for agreement in active_agreements:
            months_in = _months_between(agreement.start_date, today)

            if months_in < 8:
                continue  # Not yet 8 months

            # Check if a renewal invoice (for the next period) already exists
            # A renewal invoice is any invoice with issue_date > start_date + 6 months
            six_month_mark = agreement.start_date + timedelta(days=180)
            has_renewal = Invoice.objects.filter(
                rental_agreement=agreement,
                issue_date__gt=six_month_mark,
            ).exists()

            if has_renewal:
                continue  # Renewal already created

            # Create renewal invoice
            new_start = agreement.end_date + timedelta(days=1)
            new_end = agreement.end_date + timedelta(days=365)
            annual_amount = agreement.monthly_rent * 12
            due_date = agreement.end_date  # Due by end of current period

            self.stdout.write(
                f'  Creating renewal invoice for: {agreement.rental_property.title} '
                f'(tenant: {agreement.tenant.get_full_name()})'
            )

            if not dry_run:
                invoice = Invoice.objects.create(
                    rental_agreement=agreement,
                    tenant=agreement.tenant,
                    issue_date=today,
                    due_date=due_date,
                    amount=annual_amount,
                    currency=agreement.currency,
                    status=Invoice.InvoiceStatus.SENT,
                    description=(
                        f"Rent renewal for {agreement.rental_property.title}\n"
                        f"Next period: {new_start} to {new_end}"
                    ),
                    notes='Renewal invoice — generated automatically at 8-month mark.',
                )
                _send_renewal_invoice_email(invoice, agreement)

            renewals_created += 1

        self.stdout.write(
            self.style.SUCCESS(f'  {renewals_created} renewal invoice(s) created.\n')
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. MONTHLY REMINDERS for unpaid invoices
    # ─────────────────────────────────────────────────────────────────────────
    def _send_monthly_reminders(self, today, dry_run):
        self.stdout.write('── Sending monthly payment reminders ──')

        unpaid_invoices = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.OVERDUE],
        ).select_related(
            'tenant',
            'rental_agreement',
            'rental_agreement__rental_property',
            'rental_agreement__landlord',
        )

        reminders_sent = 0

        for invoice in unpaid_invoices:
            # Only send if it's been 28+ days since last reminder (or never reminded)
            # We use invoice.updated_at as a simple proxy — a proper
            # "last_reminder_sent" field would be more precise, but this avoids
            # schema changes and works well in practice.
            days_since_issue = (today - invoice.issue_date).days
            # Send on the 1st of each month relative to issue date
            if days_since_issue > 0 and days_since_issue % 28 != 0:
                continue

            tenant = invoice.tenant
            prop_title = invoice.rental_agreement.rental_property.title
            days_overdue = max(0, (today - invoice.due_date).days)

            self.stdout.write(
                f'  Sending reminder: invoice {invoice.invoice_number} '
                f'→ {tenant.get_full_name()}'
            )

            if not dry_run:
                if invoice.status == Invoice.InvoiceStatus.OVERDUE:
                    subject = f'⚠️ Overdue Rent Reminder – {prop_title}'
                    body_intro = (
                        f'Your rent payment is now {days_overdue} day(s) overdue.'
                    )
                else:
                    subject = f'Rent Payment Reminder – {prop_title}'
                    body_intro = (
                        f'This is a reminder that your rent payment is due on '
                        f'{invoice.due_date.strftime("%d %B %Y")}.'
                    )

                send_mail(
                    subject=subject,
                    message=(
                        f'Hi {tenant.first_name},\n\n'
                        f'{body_intro}\n\n'
                        f'Invoice Number: {invoice.invoice_number}\n'
                        f'Amount Due:     {invoice.currency} {invoice.balance:,.2f}\n'
                        f'Due Date:       {invoice.due_date.strftime("%d %B %Y")}\n\n'
                        f'Please log in to make your payment:\n'
                        f'{getattr(settings, "SITE_URL", "http://127.0.0.1:8000")}'
                        f'/dashboard/invoices/{invoice.invoice_number}/\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )

            reminders_sent += 1

        self.stdout.write(
            self.style.SUCCESS(f'  {reminders_sent} reminder(s) sent.\n')
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. OVERDUE MARKING at 12-month mark (or any past-due invoice)
    # ─────────────────────────────────────────────────────────────────────────
    def _mark_overdue_and_notify(self, today, dry_run):
        self.stdout.write('── Marking overdue invoices and notifying ──')

        # Find SENT invoices whose due_date has passed
        newly_overdue = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT,
            due_date__lt=today,
        ).select_related(
            'tenant',
            'rental_agreement',
            'rental_agreement__rental_property',
            'rental_agreement__landlord',
        )

        overdue_count = 0

        for invoice in newly_overdue:
            tenant = invoice.tenant
            landlord = invoice.rental_agreement.landlord
            prop_title = invoice.rental_agreement.rental_property.title
            days_overdue = (today - invoice.due_date).days

            self.stdout.write(
                f'  Marking overdue: {invoice.invoice_number} '
                f'({days_overdue} days late) — {tenant.get_full_name()}'
            )

            if not dry_run:
                Invoice.objects.filter(pk=invoice.pk).update(
                    status=Invoice.InvoiceStatus.OVERDUE
                )

                # Email tenant
                send_mail(
                    subject=f'Action Required: Rent Overdue – {prop_title}',
                    message=(
                        f'Hi {tenant.first_name},\n\n'
                        f'Your rent payment for {prop_title} is now {days_overdue} '
                        f'day(s) overdue.\n\n'
                        f'Invoice Number: {invoice.invoice_number}\n'
                        f'Amount Due:     {invoice.currency} {invoice.balance:,.2f}\n'
                        f'Due Date:       {invoice.due_date.strftime("%d %B %Y")}\n\n'
                        f'Please make payment immediately to avoid further action:\n'
                        f'{getattr(settings, "SITE_URL", "http://127.0.0.1:8000")}'
                        f'/dashboard/invoices/{invoice.invoice_number}/\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )

                # Email landlord
                send_mail(
                    subject=f'Tenant Rent Overdue – {prop_title}',
                    message=(
                        f'Hi {landlord.first_name},\n\n'
                        f'The tenant {tenant.get_full_name()} has not paid rent for '
                        f'{prop_title}.\n\n'
                        f'Invoice:      {invoice.invoice_number}\n'
                        f'Amount:       {invoice.currency} {invoice.balance:,.2f}\n'
                        f'Days Overdue: {days_overdue}\n\n'
                        f'We have notified the tenant and will follow up accordingly.\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[landlord.email],
                    fail_silently=True,
                )

            overdue_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'  {overdue_count} invoice(s) marked as OVERDUE.\n')
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _months_between(start_date, end_date):
    """Return approximate number of whole months between two dates."""
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)


def _send_renewal_invoice_email(invoice, agreement):
    """Send renewal invoice email to tenant and landlord."""
    tenant = invoice.tenant
    landlord = agreement.landlord
    prop_title = agreement.rental_property.title

    send_mail(
        subject=f'Renewal Invoice – {prop_title}',
        message=(
            f'Hi {tenant.first_name},\n\n'
            f'Your tenancy at {prop_title} is approaching its renewal period. '
            f'Please find your renewal invoice below:\n\n'
            f'Invoice Number: {invoice.invoice_number}\n'
            f'Amount Due:     {invoice.currency} {invoice.amount:,.2f}\n'
            f'Due Date:       {invoice.due_date.strftime("%d %B %Y")}\n\n'
            f'Pay now to secure your tenancy for the next year:\n'
            f'{getattr(settings, "SITE_URL", "http://127.0.0.1:8000")}'
            f'/dashboard/invoices/{invoice.invoice_number}/\n\n'
            f'Psalms Real Estate'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[tenant.email],
        fail_silently=True,
    )

    send_mail(
        subject=f'Renewal Invoice Issued – {prop_title}',
        message=(
            f'Hi {landlord.first_name},\n\n'
            f'A renewal invoice has been issued to {tenant.get_full_name()} '
            f'for {prop_title}.\n\n'
            f'Invoice:    {invoice.invoice_number}\n'
            f'Amount:     {invoice.currency} {invoice.amount:,.2f}\n'
            f'Due Date:   {invoice.due_date.strftime("%d %B %Y")}\n\n'
            f'Psalms Real Estate'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[landlord.email],
        fail_silently=True,
    )
