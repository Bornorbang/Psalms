"""
Django signals for automated business logic:

1. When a RentalAgreement is saved with status=ACTIVE for the first time:
   - Create the initial rent invoice (annual amount, due within 7 days)
   - Mark the property as RENTED (removes it from public listings)
   - Send invoice notification email to tenant

2. When a RentalAgreement is TERMINATED or EXPIRED:
   - Mark the property back as AVAILABLE
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta


@receiver(pre_save, sender='app.RentalAgreement')
def track_agreement_status_change(sender, instance, **kwargs):
    """Store old status before save so post_save can detect changes."""
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None  # New record


@receiver(post_save, sender='app.RentalAgreement')
def on_rental_agreement_saved(sender, instance, created, **kwargs):
    """
    After a RentalAgreement is saved:
    - If it just became ACTIVE → auto-create first invoice + mark property RENTED
    - If it became TERMINATED/EXPIRED → mark property AVAILABLE
    """
    from app.models import Invoice, Property

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    just_activated = new_status == 'ACTIVE' and old_status != 'ACTIVE'
    just_closed = new_status in ('TERMINATED', 'EXPIRED') and old_status == 'ACTIVE'

    # ── Activated ───────────────────────────────────────────────────────────
    if just_activated:
        # 1. Mark property as RENTED
        prop = instance.rental_property
        if prop.status != Property.PropertyStatus.RENTED:
            Property.objects.filter(pk=prop.pk).update(
                status=Property.PropertyStatus.RENTED
            )

        # 2. Create first invoice if none exists yet for this agreement
        existing = Invoice.objects.filter(rental_agreement=instance).exists()
        if not existing:
            today = timezone.now().date()
            due_date = today + timedelta(days=7)

            # Annual (yearly) rent stored directly in the monthly_rent field
            annual_amount = instance.monthly_rent

            invoice = Invoice.objects.create(
                rental_agreement=instance,
                tenant=instance.tenant,
                issue_date=today,
                due_date=due_date,
                amount=annual_amount,
                currency=instance.currency,
                status=Invoice.InvoiceStatus.SENT,
                description=(
                    f"Annual rent for {instance.rental_property.title}\n"
                    f"Period: {instance.start_date} to {instance.end_date}"
                ),
            )

            # 3. Send invoice email to tenant
            _send_invoice_email(invoice, instance)

    # ── Closed ──────────────────────────────────────────────────────────────
    elif just_closed:
        prop = instance.rental_property
        # Only make available if no other active agreement on this property
        other_active = sender.objects.filter(
            rental_property=prop,
            status='ACTIVE'
        ).exclude(pk=instance.pk).exists()

        if not other_active:
            Property.objects.filter(pk=prop.pk).update(
                status=Property.PropertyStatus.AVAILABLE
            )


def _send_invoice_email(invoice, agreement):
    """Send invoice notification email to tenant and landlord."""
    tenant = invoice.tenant
    landlord = agreement.landlord
    prop_title = agreement.rental_property.title

    # To tenant
    send_mail(
        subject=f'Your Rent Invoice is Ready – {prop_title}',
        message=(
            f'Hi {tenant.first_name},\n\n'
            f'Your rental agreement for {prop_title} is now active. '
            f'Please find your invoice details below:\n\n'
            f'Invoice Number: {invoice.invoice_number}\n'
            f'Amount Due:     {invoice.currency} {invoice.amount:,.2f}\n'
            f'Due Date:       {invoice.due_date.strftime("%d %B %Y")}\n\n'
            f'Please log in to your dashboard to make payment:\n'
            f'{settings.SITE_URL if hasattr(settings, "SITE_URL") else "http://127.0.0.1:8000"}'
            f'/dashboard/invoices/{invoice.invoice_number}/\n\n'
            f'Psalms Real Estate'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[tenant.email],
        fail_silently=True,
    )

    # To landlord
    send_mail(
        subject=f'Tenant Invoice Issued – {prop_title}',
        message=(
            f'Hi {landlord.first_name},\n\n'
            f'A rental agreement has been activated for your property {prop_title}.\n\n'
            f'Tenant:         {tenant.get_full_name()}\n'
            f'Invoice Number: {invoice.invoice_number}\n'
            f'Amount:         {invoice.currency} {invoice.amount:,.2f}\n'
            f'Due Date:       {invoice.due_date.strftime("%d %B %Y")}\n\n'
            f'Psalms Real Estate'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[landlord.email],
        fail_silently=True,
    )
