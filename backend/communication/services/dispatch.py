import logging

from django.db.models import Count, Q
from django.utils import timezone

from communication.models import Campaign, CampaignMessage
from .providers import ProviderManager
from .campaigns import queue_campaign

logger = logging.getLogger(__name__)


def _refresh_campaign(campaign):
    counts = dict(campaign.messages.filter(is_test=False).values('status').annotate(total=Count('id')).values_list('status', 'total'))
    campaign.sent_count = counts.get('sent', 0) + counts.get('delivered', 0)
    campaign.delivered_count = counts.get('delivered', 0)
    campaign.failed_count = counts.get('failed', 0)
    campaign.skipped_count = counts.get('skipped', 0)
    remaining = counts.get('queued', 0) + counts.get('pending', 0)
    if remaining == 0:
        campaign.status = 'sent' if campaign.sent_count else 'failed'
        campaign.finished_at = timezone.now()
    campaign.save(update_fields=['sent_count', 'delivered_count', 'failed_count', 'skipped_count', 'status', 'finished_at', 'updated_at'])


def dispatch_message(message):
    campaign = message.campaign
    try:
        provider = ProviderManager.get(campaign.provider)
        if campaign.channel == 'sms':
            result = provider.send_single(to=message.recipient_phone, message=message.rendered_body)
        else:
            result = provider.send_single(
                to=message.recipient_email, subject=message.rendered_subject,
                body=message.rendered_body, body_type=campaign.body_type,
            )
        message.status = 'sent'
        message.provider_message_id = result.get('message_id', '')
        message.provider_response = result.get('response', {})
        message.sent_at = timezone.now()
        message.error_message = ''
        message.save()
    except Exception as exc:
        message.status = 'failed'
        message.failed_at = timezone.now()
        message.retry_count += 1
        message.error_message = str(exc)[:1000]
        message.save()
        logger.warning('Campaign message %s failed: %s', message.id, exc)


def process_communication_queue(batch_size=25):
    for due_campaign in Campaign.objects.filter(status='scheduled', scheduled_at__lte=timezone.now()).order_by('scheduled_at')[:10]:
        try:
            queue_campaign(due_campaign, allowed_statuses=('scheduled',))
        except ValueError as exc:
            due_campaign.status = 'failed'
            due_campaign.finished_at = timezone.now()
            due_campaign.settings = {**(due_campaign.settings or {}), 'schedule_error': str(exc)}
            due_campaign.save(update_fields=['status', 'finished_at', 'settings', 'updated_at'])
    campaign = Campaign.objects.filter(status__in=['queued', 'sending']).order_by('created_at').first()
    if not campaign:
        return
    if campaign.status == 'queued':
        campaign.status = 'sending'
        campaign.started_at = campaign.started_at or timezone.now()
        campaign.save(update_fields=['status', 'started_at', 'updated_at'])
    for message in campaign.messages.filter(status='queued').order_by('created_at')[:batch_size]:
        dispatch_message(message)
    _refresh_campaign(campaign)
