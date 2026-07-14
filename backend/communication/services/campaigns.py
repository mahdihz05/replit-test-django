from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from communication.models import CampaignMessage, Contact
from .templates import render_template


def campaign_contacts(campaign):
    contact_ids = set(campaign.selected_contacts.values_list('id', flat=True))
    contact_ids.update(Contact.objects.filter(groups__in=campaign.selected_groups.all()).values_list('id', flat=True))
    return Contact.objects.filter(id__in=contact_ids, workspace=campaign.workspace, status='active').distinct()


@transaction.atomic
def queue_campaign(campaign, allowed_statuses=('draft',)):
    if campaign.status not in allowed_statuses:
        raise ValueError('فقط کمپین پیش‌نویس قابل شروع است')
    contacts = list(campaign_contacts(campaign))
    if not contacts:
        raise ValueError('کمپین هیچ مخاطبی ندارد')
    messages, invalid = [], 0
    for contact in contacts:
        destination = contact.phone if campaign.channel == 'sms' else contact.email
        if not destination:
            invalid += 1
            continue
        messages.append(CampaignMessage(
            campaign=campaign,
            contact=contact,
            recipient_name=contact.name,
            recipient_phone=contact.phone,
            recipient_email=contact.email,
            rendered_subject=render_template(campaign.subject, contact),
            rendered_body=render_template(campaign.body, contact),
            status='queued',
            queued_at=timezone.now(),
        ))
    CampaignMessage.objects.bulk_create(messages)
    campaign.recipients_count = len(contacts)
    campaign.valid_recipients_count = len(messages)
    campaign.invalid_recipients_count = invalid
    campaign.status = 'queued'
    campaign.save(update_fields=[
        'recipients_count', 'valid_recipients_count', 'invalid_recipients_count', 'status', 'updated_at'
    ])
    return len(messages)


def campaign_preview(campaign, limit=5):
    contacts = campaign_contacts(campaign)[:limit]
    return [{
        'contact_id': str(contact.id),
        'name': contact.name,
        'recipient': contact.phone if campaign.channel == 'sms' else contact.email,
        'subject': render_template(campaign.subject, contact),
        'body': render_template(campaign.body, contact),
    } for contact in contacts]
