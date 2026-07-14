import json
import logging
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_engine import openai_client
from config.ai import get_wallet_cost
from wallet.models import Wallet, WalletTransaction
from workspaces.models import WorkspaceMember

from .models import Campaign, CampaignMessage, CommunicationProvider, Contact, ContactGroup, ImportJob, MessageTemplate
from .serializers import (
    CampaignMessageSerializer, CampaignSerializer, CommunicationProviderSerializer, ContactGroupSerializer,
    ContactSerializer, ImportJobSerializer, MessageTemplateSerializer,
)
from .services.campaigns import campaign_preview, queue_campaign
from .services.dispatch import dispatch_message
from .services.imports import analyze_rows, map_row, read_import_file, validate_contact_data
from .services.providers import ProviderManager
from .services.templates import DEFAULT_VARIABLES, render_template

logger = logging.getLogger(__name__)


def _workspace(request, workspace_id):
    member = WorkspaceMember.objects.select_related('workspace').filter(workspace_id=workspace_id, user=request.user).first()
    return member.workspace if member else None


def _forbidden():
    return Response({'success': False, 'error': 'دسترسی ندارید'}, status=status.HTTP_403_FORBIDDEN)


def _payload(data):
    return {'success': True, 'data': data}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    campaigns = Campaign.objects.filter(workspace=workspace)
    contacts = Contact.objects.filter(workspace=workspace)
    totals = campaigns.aggregate(
        sent=Count('messages', filter=Q(messages__status__in=['sent', 'delivered'], messages__is_test=False)),
        failed=Count('messages', filter=Q(messages__status='failed', messages__is_test=False)),
    )
    recent = CampaignSerializer(campaigns[:5], many=True, context={'workspace': workspace}).data
    return Response(_payload({
        'total_campaigns': campaigns.count(), 'sms_campaigns': campaigns.filter(channel='sms').count(),
        'email_campaigns': campaigns.filter(channel='email').count(), 'total_contacts': contacts.count(),
        'sent_messages': totals['sent'] or 0, 'failed_messages': totals['failed'] or 0,
        'running_campaigns': campaigns.filter(status__in=['scheduled', 'queued', 'sending']).count(),
        'ai_generated_messages': campaigns.filter(settings__ai_generated=True).count(), 'recent_campaigns': recent,
    }))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def providers(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if request.method == 'GET':
        queryset = CommunicationProvider.objects.filter(workspace=workspace)
        return Response(_payload(CommunicationProviderSerializer(queryset, many=True).data))
    serializer = CommunicationProviderSerializer(data=request.data)
    if serializer.is_valid():
        try:
            provider = serializer.save(workspace=workspace, created_by=request.user)
        except ImproperlyConfigured:
            logger.exception('Provider credential encryption is not configured')
            return Response({
                'success': False,
                'error': 'کلید رمزنگاری اطلاعات اتصال روی سرور تنظیم نشده است.',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(_payload(CommunicationProviderSerializer(provider).data), status=201)
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def provider_detail(request, workspace_id, provider_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    provider = CommunicationProvider.objects.filter(workspace=workspace, id=provider_id).first()
    if not provider: return Response({'error': 'Provider یافت نشد'}, status=404)
    if request.method == 'DELETE':
        if provider.campaigns.exists():
            provider.status = 'disabled'; provider.save(update_fields=['status', 'updated_at'])
        else: provider.delete()
        return Response(status=204)
    if request.method == 'GET': return Response(_payload(CommunicationProviderSerializer(provider).data))
    serializer = CommunicationProviderSerializer(provider, data=request.data, partial=request.method == 'PATCH')
    if serializer.is_valid():
        return Response(_payload(CommunicationProviderSerializer(serializer.save()).data))
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def provider_test(request, workspace_id, provider_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    provider = CommunicationProvider.objects.filter(workspace=workspace, id=provider_id).first()
    if not provider: return Response({'error': 'Provider یافت نشد'}, status=404)
    try:
        result = ProviderManager.get(provider).test_connection()
        provider.last_test_status, provider.last_test_error = 'connected', ''
        code = 200
    except Exception as exc:
        result = None; provider.last_test_status, provider.last_test_error = 'failed', str(exc)[:500]; code = 400
    provider.last_tested_at = timezone.now(); provider.save()
    return Response({'success': code == 200, 'data': result, 'error': provider.last_test_error}, status=code)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def contacts(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if request.method == 'GET':
        queryset = Contact.objects.filter(workspace=workspace)
        search = request.GET.get('search', '').strip()
        if search: queryset = queryset.filter(Q(name__icontains=search) | Q(phone__icontains=search) | Q(email__icontains=search) | Q(company__icontains=search))
        if request.GET.get('status'): queryset = queryset.filter(status=request.GET['status'])
        if request.GET.get('group'): queryset = queryset.filter(groups__id=request.GET['group'])
        return Response(_payload(ContactSerializer(queryset.distinct(), many=True).data))
    serializer = ContactSerializer(data=request.data, context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(ContactSerializer(serializer.save(workspace=workspace, created_by=request.user)).data), status=201)
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def contact_detail(request, workspace_id, contact_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    contact = Contact.objects.filter(workspace=workspace, id=contact_id).first()
    if not contact: return Response({'error': 'مخاطب یافت نشد'}, status=404)
    if request.method == 'DELETE': contact.delete(); return Response(status=204)
    if request.method == 'GET': return Response(_payload(ContactSerializer(contact).data))
    serializer = ContactSerializer(contact, data=request.data, partial=request.method == 'PATCH', context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(ContactSerializer(serializer.save()).data))
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def groups(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if request.method == 'GET':
        queryset = ContactGroup.objects.filter(workspace=workspace).annotate(contact_count=Count('contacts'))
        return Response(_payload(ContactGroupSerializer(queryset, many=True, context={'workspace': workspace}).data))
    serializer = ContactGroupSerializer(data=request.data, context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(ContactGroupSerializer(serializer.save(workspace=workspace, created_by=request.user), context={'workspace': workspace}).data), status=201)
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def group_detail(request, workspace_id, group_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    group = ContactGroup.objects.filter(workspace=workspace, id=group_id).first()
    if not group: return Response({'error': 'گروه یافت نشد'}, status=404)
    if request.method == 'DELETE': group.delete(); return Response(status=204)
    serializer = ContactGroupSerializer(group, data=request.data, partial=request.method == 'PATCH', context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(ContactGroupSerializer(serializer.save(), context={'workspace': workspace}).data))
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def group_add_contacts(request, workspace_id, group_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    group = ContactGroup.objects.filter(workspace=workspace, id=group_id).first()
    if not group: return Response({'error': 'گروه یافت نشد'}, status=404)
    group.contacts.add(*Contact.objects.filter(workspace=workspace, id__in=request.data.get('contact_ids', [])))
    return Response(_payload({'contact_count': group.contacts.count()}))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def group_remove_contact(request, workspace_id, group_id, contact_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    group = ContactGroup.objects.filter(workspace=workspace, id=group_id).first()
    if not group: return Response({'error': 'گروه یافت نشد'}, status=404)
    group.contacts.remove(contact_id); return Response(status=204)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def templates(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if request.method == 'GET':
        queryset = MessageTemplate.objects.filter(workspace=workspace)
        if request.GET.get('channel'): queryset = queryset.filter(channel=request.GET['channel'])
        return Response(_payload(MessageTemplateSerializer(queryset, many=True).data))
    serializer = MessageTemplateSerializer(data=request.data)
    if serializer.is_valid(): return Response(_payload(MessageTemplateSerializer(serializer.save(workspace=workspace, created_by=request.user)).data), status=201)
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def template_detail(request, workspace_id, template_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    template = MessageTemplate.objects.filter(workspace=workspace, id=template_id).first()
    if not template: return Response({'error': 'قالب یافت نشد'}, status=404)
    if request.method == 'DELETE': template.delete(); return Response(status=204)
    if request.method == 'GET': return Response(_payload(MessageTemplateSerializer(template).data))
    serializer = MessageTemplateSerializer(template, data=request.data, partial=request.method == 'PATCH')
    if serializer.is_valid(): return Response(_payload(MessageTemplateSerializer(serializer.save()).data))
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def template_preview(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    contact = Contact.objects.filter(workspace=workspace, id=request.data.get('contact_id')).first()
    return Response(_payload({'subject': render_template(request.data.get('subject', ''), contact), 'body': render_template(request.data.get('body', ''), contact), 'available_variables': DEFAULT_VARIABLES}))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def campaigns(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if request.method == 'GET':
        queryset = Campaign.objects.filter(workspace=workspace).select_related('provider')
        for key in ('channel', 'status'):
            if request.GET.get(key): queryset = queryset.filter(**{key: request.GET[key]})
        if request.GET.get('provider'): queryset = queryset.filter(provider_id=request.GET['provider'])
        if request.GET.get('search'): queryset = queryset.filter(name__icontains=request.GET['search'])
        return Response(_payload(CampaignSerializer(queryset, many=True, context={'workspace': workspace}).data))
    serializer = CampaignSerializer(data=request.data, context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(CampaignSerializer(serializer.save(workspace=workspace, created_by=request.user), context={'workspace': workspace}).data), status=201)
    return Response({'success': False, 'error': serializer.errors}, status=400)


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def campaign_detail(request, workspace_id, campaign_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    campaign = Campaign.objects.filter(workspace=workspace, id=campaign_id).select_related('provider').first()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    if request.method == 'DELETE':
        if campaign.status not in ('draft', 'cancelled'): return Response({'error': 'کمپین فعال قابل حذف نیست'}, status=400)
        campaign.delete(); return Response(status=204)
    if request.method == 'GET': return Response(_payload(CampaignSerializer(campaign, context={'workspace': workspace}).data))
    if campaign.status != 'draft': return Response({'error': 'فقط پیش‌نویس قابل ویرایش است'}, status=400)
    serializer = CampaignSerializer(campaign, data=request.data, partial=request.method == 'PATCH', context={'workspace': workspace})
    if serializer.is_valid(): return Response(_payload(CampaignSerializer(serializer.save(), context={'workspace': workspace}).data))
    return Response({'success': False, 'error': serializer.errors}, status=400)


def _campaign_for(request, workspace_id, campaign_id):
    workspace = _workspace(request, workspace_id)
    return workspace, Campaign.objects.filter(workspace=workspace, id=campaign_id).select_related('provider').first() if workspace else None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def campaign_preview_view(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    return Response(_payload({'samples': campaign_preview(campaign), 'variables': DEFAULT_VARIABLES}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def campaign_start(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    try: count = queue_campaign(campaign)
    except ValueError as exc: return Response({'error': str(exc)}, status=400)
    return Response(_payload({'status': 'queued', 'messages': count}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def campaign_schedule(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    if campaign.status != 'draft': return Response({'error': 'فقط پیش‌نویس قابل زمان‌بندی است'}, status=400)
    scheduled_at = parse_datetime(str(request.data.get('scheduled_at', '')))
    if not scheduled_at:
        return Response({'error': 'زمان ارسال معتبر نیست'}, status=400)
    if timezone.is_naive(scheduled_at):
        scheduled_at = timezone.make_aware(scheduled_at, timezone.get_current_timezone())
    if scheduled_at <= timezone.now():
        return Response({'error': 'زمان ارسال باید در آینده باشد'}, status=400)
    campaign.scheduled_at = scheduled_at
    campaign.status = 'scheduled'
    campaign.save(update_fields=['scheduled_at', 'status', 'updated_at'])
    return Response(_payload({'status': 'scheduled', 'scheduled_at': scheduled_at}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def campaign_cancel(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    if campaign.status in ('sent', 'failed'): return Response({'error': 'کمپین پایان یافته است'}, status=400)
    campaign.status = 'cancelled'; campaign.finished_at = timezone.now(); campaign.save()
    campaign.messages.filter(status__in=['pending', 'queued']).update(status='skipped')
    return Response(_payload({'status': 'cancelled'}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def campaign_send_test(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    recipient = str(request.data.get('recipient', '')).strip()
    if not recipient: return Response({'error': 'گیرنده تست الزامی است'}, status=400)
    contact = Contact.objects.filter(workspace=workspace, id=request.data.get('contact_id')).first()
    message = CampaignMessage.objects.create(
        campaign=campaign, contact=contact, recipient_name=getattr(contact, 'name', ''),
        recipient_phone=recipient if campaign.channel == 'sms' else '', recipient_email=recipient if campaign.channel == 'email' else '',
        rendered_subject=render_template(campaign.subject, contact), rendered_body=render_template(campaign.body, contact),
        status='queued', is_test=True, queued_at=timezone.now(),
    )
    dispatch_message(message); message.refresh_from_db()
    code = 200 if message.status == 'sent' else 400
    return Response(_payload(CampaignMessageSerializer(message).data) if code == 200 else {'success': False, 'error': message.error_message}, status=code)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def campaign_report(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    campaign_data = CampaignSerializer(campaign, context={'workspace': workspace}).data
    campaign_data['failure_rate'] = round((campaign.failed_count / campaign.valid_recipients_count) * 100, 1) if campaign.valid_recipients_count else 0
    return Response(_payload(campaign_data))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def campaign_messages(request, workspace_id, campaign_id):
    workspace, campaign = _campaign_for(request, workspace_id, campaign_id)
    if not workspace: return _forbidden()
    if not campaign: return Response({'error': 'کمپین یافت نشد'}, status=404)
    queryset = campaign.messages.all()
    if request.GET.get('status'): queryset = queryset.filter(status=request.GET['status'])
    if request.GET.get('search'):
        term = request.GET['search']; queryset = queryset.filter(Q(recipient_name__icontains=term) | Q(recipient_phone__icontains=term) | Q(recipient_email__icontains=term))
    return Response(_payload(CampaignMessageSerializer(queryset, many=True).data))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def import_preview(request, workspace_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    uploaded = request.FILES.get('file')
    if not uploaded: return Response({'error': 'فایل الزامی است'}, status=400)
    suffix = Path(uploaded.name).suffix.lower().lstrip('.')
    if suffix not in ('csv', 'xlsx'): return Response({'error': 'فقط CSV و XLSX مجاز است'}, status=400)
    try: rows = read_import_file(uploaded, suffix)
    except Exception as exc: return Response({'error': str(exc)}, status=400)
    columns = list(rows[0].keys()) if rows else []
    raw_mapping = request.data.get('mapping', '{}')
    mapping = json.loads(raw_mapping) if isinstance(raw_mapping, str) else raw_mapping
    if not mapping:
        aliases = {'mobile': 'phone', 'phone_number': 'phone', 'نام': 'name', 'موبایل': 'phone', 'ایمیل': 'email', 'شرکت': 'company', 'شهر': 'city'}
        mapping = {column: aliases.get(column.strip().lower(), column.strip().lower()) for column in columns if aliases.get(column.strip().lower(), column.strip().lower()) in ('name', 'phone', 'email', 'company', 'city', 'tags')}
    analysis = analyze_rows(workspace, rows, mapping) if mapping else {'total': len(rows), 'valid': 0, 'invalid': 0, 'duplicates': 0, 'errors': [], 'preview': rows[:10]}
    uploaded.seek(0)
    job = ImportJob.objects.create(
        workspace=workspace, created_by=request.user, file=uploaded, file_name=uploaded.name, file_type=suffix,
        total_rows=analysis['total'], valid_rows=analysis['valid'], invalid_rows=analysis['invalid'],
        duplicate_rows=analysis['duplicates'], mapping=mapping, errors=analysis['errors'][:100], preview=analysis['preview'],
    )
    data = ImportJobSerializer(job).data; data['columns'] = columns
    return Response(_payload(data), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_confirm(request, workspace_id, job_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    job = ImportJob.objects.filter(workspace=workspace, id=job_id, status='previewed').first()
    if not job: return Response({'error': 'Import Job یافت نشد'}, status=404)
    mapping = request.data.get('mapping') or job.mapping
    rows = read_import_file(job.file, job.file_type)
    created, invalid, duplicates = 0, 0, 0
    for row in rows:
        data = map_row(row, mapping); errors = validate_contact_data(data)
        if errors: invalid += 1; continue
        if (data['phone'] and Contact.objects.filter(workspace=workspace, phone=data['phone']).exists()) or (data['email'] and Contact.objects.filter(workspace=workspace, email=data['email']).exists()):
            duplicates += 1; continue
        Contact.objects.create(workspace=workspace, created_by=request.user, **data); created += 1
    job.mapping = mapping; job.valid_rows = created; job.invalid_rows = invalid; job.duplicate_rows = duplicates; job.status = 'completed'; job.save()
    return Response(_payload({'created': created, 'invalid': invalid, 'duplicates': duplicates}))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_remap_preview(request, workspace_id, job_id):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    job = ImportJob.objects.filter(workspace=workspace, id=job_id, status='previewed').first()
    if not job: return Response({'error': 'Import Job یافت نشد'}, status=404)
    mapping = request.data.get('mapping') or {}
    if not mapping: return Response({'error': 'Mapping الزامی است'}, status=400)
    try:
        rows = read_import_file(job.file, job.file_type)
        analysis = analyze_rows(workspace, rows, mapping)
    except Exception as exc:
        return Response({'error': str(exc)}, status=400)
    job.mapping = mapping
    job.total_rows = analysis['total']; job.valid_rows = analysis['valid']; job.invalid_rows = analysis['invalid']
    job.duplicate_rows = analysis['duplicates']; job.errors = analysis['errors'][:100]; job.preview = analysis['preview']
    job.save()
    data = ImportJobSerializer(job).data
    data['columns'] = list(rows[0].keys()) if rows else []
    return Response(_payload(data))


AI_ACTIONS = {
    'sms-generate': ('sms_ai_generate', 'Generate three Persian SMS variants as JSON: {"variants":[{"title":"...","body":"..."}],"suggested_variables":[],"notes":""}.'),
    'sms-rewrite': ('sms_ai_rewrite', 'Rewrite the Persian SMS in three tones and return the same JSON variant structure.'),
    'sms-shorten': ('sms_ai_shorten', 'Shorten the Persian SMS while preserving CTA and return the same JSON variant structure.'),
    'email-generate': ('campaign_ai_generate_bundle', 'Generate Persian email copy as JSON: {"subjects":["..."],"bodies":[{"title":"...","body":"..."}],"cta_suggestions":["..."]}.'),
    'email-rewrite': ('email_ai_rewrite', 'Rewrite the Persian email in formal and friendly variants using the email JSON structure.'),
}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_assist(request, workspace_id, action):
    workspace = _workspace(request, workspace_id)
    if not workspace: return _forbidden()
    if action not in AI_ACTIONS: return Response({'error': 'عملیات AI نامعتبر است'}, status=404)
    operation, instruction = AI_ACTIONS[action]; cost = get_wallet_cost(operation)
    wallet = Wallet.objects.filter(workspace=workspace).first()
    if not wallet or wallet.balance < cost: return Response({'error': 'موجودی کافی نیست'}, status=402)
    prompt = str(request.data.get('prompt') or request.data.get('text') or '').strip()
    if not prompt: return Response({'error': 'توضیح یا متن الزامی است'}, status=400)
    raw, error, tokens = openai_client._call_chat(
        'You are a Persian marketing communication expert. Return valid JSON only.',
        f'{instruction}\nUser request:\n{prompt}', response_format={'type': 'json_object'},
        operation_name=operation, max_retries=2,
    )
    if error: return Response({'error': error}, status=503)
    try: result = json.loads(raw)
    except json.JSONDecodeError: result = {'text': raw}
    with transaction.atomic():
        wallet.balance -= cost; wallet.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(wallet=wallet, type='deduct', amount=cost, description=f'{operation} (tokens: {tokens})')
    return Response(_payload({'result': result, 'cost': cost, 'tokens': tokens}))
