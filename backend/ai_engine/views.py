from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from wallet.models import Wallet, WalletTransaction
from django.conf import settings

from .models import AIChatSession, AIChatMessage, GenerationBatch, GeneratedItem
from .serializers import AIChatSessionSerializer, AIChatSessionListSerializer, AIChatMessageSerializer, GeneratedItemSerializer
from . import openai_client


def get_member(user, workspace_id):
    try:
        return WorkspaceMember.objects.get(workspace_id=workspace_id, user=user)
    except WorkspaceMember.DoesNotExist:
        return None


def check_wallet(workspace_id, cost):
    try:
        wallet = Wallet.objects.get(workspace_id=workspace_id)
        if wallet.balance < cost:
            return None, 'موجودی کافی نیست'
        return wallet, None
    except Wallet.DoesNotExist:
        return None, 'کیف پول یافت نشد'


def deduct_wallet(wallet, cost, description):
    wallet.balance -= cost
    wallet.save()
    WalletTransaction.objects.create(
        wallet=wallet,
        type='deduct',
        amount=cost,
        description=description
    )


def _create_batch_and_text_item(workspace_id, user, mode, capability, request_data, text_content):
    """Create a GenerationBatch + text GeneratedItem for standard modes that opt-in to image."""
    batch = GenerationBatch.objects.create(
        workspace_id=workspace_id,
        user=user,
        mode=mode,
        capability=capability,
        topic=request_data.get('topic', request_data.get('goal', request_data.get('niche', request_data.get('text', '')))),
        tone=request_data.get('tone', 'حرفه‌ای'),
        platform=request_data.get('platform', ''),
        variant_count=None,
    )
    item = GeneratedItem.objects.create(
        batch=batch,
        item_type='full_text',
        order=0,
        content=text_content
    )
    return batch, item


def _generate_image_for_batch(batch, source_text, wallet, cost, platform=''):
    """Generate a DALL-E image from source text and attach it to the batch as a GeneratedItem."""
    batch.image_status = 'pending'
    batch.save(update_fields=['image_status'])
    image_path, error = openai_client.generate_image_from_text(source_text, platform=platform)
    if error or not image_path:
        batch.image_status = 'failed'
        batch.save(update_fields=['image_status'])
        return None, error or 'تولید تصویر با خطا مواجه شد'

    image_item = GeneratedItem.objects.create(
        batch=batch,
        item_type='image',
        order=99,
        content='',
        image=image_path
    )
    batch.image_status = 'success'
    batch.save(update_fields=['image_status'])
    if wallet and cost:
        deduct_wallet(wallet, cost, f'تولید تصویر - {batch.topic[:50]}')
    return image_item, None


@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def chat_sessions(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        sessions = AIChatSession.objects.filter(workspace_id=workspace_id, user=request.user)
        return Response({'success': True, 'data': AIChatSessionListSerializer(sessions, many=True).data})

    session = AIChatSession.objects.create(
        workspace_id=workspace_id,
        user=request.user,
        content_id=request.data.get('content_id')
    )
    return Response({'success': True, 'data': AIChatSessionSerializer(session).data},
                    status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_session_detail(request, workspace_id, session_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        session = AIChatSession.objects.get(id=session_id, workspace_id=workspace_id, user=request.user)
    except AIChatSession.DoesNotExist:
        return Response({'success': False, 'error': 'جلسه یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    return Response({'success': True, 'data': AIChatSessionSerializer(session).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request, workspace_id, session_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        session = AIChatSession.objects.get(id=session_id, workspace_id=workspace_id, user=request.user)
    except AIChatSession.DoesNotExist:
        return Response({'success': False, 'error': 'جلسه یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    user_message = request.data.get('message', '')
    if not user_message:
        return Response({'success': False, 'error': 'پیام خالی است', 'code': 'EMPTY_MESSAGE'},
                        status=status.HTTP_400_BAD_REQUEST)

    AIChatMessage.objects.create(session=session, role='user', type='text', body=user_message)

    if session.title == 'New Chat':
        session.title = user_message[:50]
        session.save()

    all_msgs = AIChatMessage.objects.filter(session=session, type='text').order_by('created_at')
    messages = [{'role': m.role, 'content': m.body} for m in all_msgs]

    result, error, tokens = openai_client.chat_completion(messages)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    ai_msg = AIChatMessage.objects.create(
        session=session,
        role='assistant',
        type='text',
        body=result,
        metadata={'tokens': tokens, 'model': 'gpt-4.1-mini'}
    )

    return Response({'success': True, 'data': AIChatMessageSerializer(ai_msg).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_text(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['text_generation']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    goal = request.data.get('goal', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_text(
        goal=goal,
        platform=platform,
        tone=request.data.get('tone', 'حرفه‌ای'),
        keywords=request.data.get('keywords', ''),
        language=request.data.get('language', 'fa'),
        word_count=request.data.get('word_count', 300),
        is_caption=bool(request.data.get('generate_image'))
    )

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'تولید متن - {goal[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'text', request.data, result
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, image_error = _generate_image_for_batch(batch, result, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'text': result, 'tokens': tokens}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_image_view(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['image_generation']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    description = request.data.get('description', '')
    platform = request.data.get('platform', '')
    result, error = openai_client.generate_image(
        description=description,
        style=request.data.get('style', ''),
        platform=platform
    )

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'تولید تصویر - {description[:50]}')
    image_url = f'/media/{result}' if result else None
    return Response({'success': True, 'data': {'image_url': image_url, 'path': result}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rewrite_text(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['content_rewrite']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    text = request.data.get('text', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.rewrite_text(text, request.data.get('tone', 'حرفه‌ای'), platform=platform)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, 'بازنویسی متن')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'rewrite', request.data, result
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, result, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'text': result, 'tokens': tokens}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_titles(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['title_suggestions']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    topic = request.data.get('topic', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.suggest_titles(topic, platform=platform)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'پیشنهاد عنوان - {topic[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'title', request.data, '\n'.join(result)
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, topic, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'titles': result}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def suggest_hashtags(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['hashtag_suggestions']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    topic = request.data.get('topic', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.suggest_hashtags(topic, platform=platform)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'پیشنهاد هشتگ - {topic[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'hashtag', request.data, '\n'.join(result)
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, topic, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'hashtags': result}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_summary(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)
    cost = settings.WALLET_COSTS.get('content_rewrite', 5)
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)
    text = request.data.get('text', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_summary(text, request.data.get('length', 'brief'), platform=platform)
    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    deduct_wallet(wallet, cost, 'خلاصه‌سازی متن')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'summary', request.data, result
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, result, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'text': result, 'tokens': tokens}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_scenario(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)
    cost = settings.WALLET_COSTS.get('text_generation', 10)
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)
    topic = request.data.get('topic', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_scenario(
        topic, platform, request.data.get('goal', ''))
    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    deduct_wallet(wallet, cost, f'سناریو محتوا - {topic[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'scenario', request.data, result
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, result, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'text': result, 'tokens': tokens}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_idea(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)
    cost = settings.WALLET_COSTS.get('title_suggestions', 5)
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)
    niche = request.data.get('niche', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_idea(
        niche, platform, int(request.data.get('count', 5)))
    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)
    deduct_wallet(wallet, cost, f'ایده محتوا - {niche[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'idea', request.data, '\n'.join(result)
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, niche, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'ideas': result, 'tokens': tokens}})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_cta(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['cta_generation']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    goal = request.data.get('goal', '')
    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_cta(goal, platform)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'تولید CTA - {goal[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            batch, item = _create_batch_and_text_item(
                workspace_id, request.user, 'standard', 'cta', request.data, '\n'.join(result)
            )
            batch.status = 'success'
            batch.wallet_cost_charged = cost
            batch.save(update_fields=['status', 'wallet_cost_charged'])
            image_item, _ = _generate_image_for_batch(batch, goal, image_wallet, image_cost, platform=platform)
            items = [item]
            if image_item:
                items.append(image_item)
            return Response({'success': True, 'data': {'items': GeneratedItemSerializer(items, many=True, context={'request': request}).data}})

    return Response({'success': True, 'data': {'ctas': result}})


# ---------------------------------------------------------------------------
# New batch generation modes: bundle and multi-variant
# ---------------------------------------------------------------------------


def _create_generation_batch(workspace_id, user, mode, capability, request_data):
    return GenerationBatch.objects.create(
        workspace_id=workspace_id,
        user=user,
        mode=mode,
        capability=capability,
        topic=request_data.get('topic', request_data.get('goal', request_data.get('niche', request_data.get('text', '')))),
        tone=request_data.get('tone', 'حرفه‌ای'),
        platform=request_data.get('platform', ''),
        variant_count=request_data.get('variant_count') if mode == 'multi_variant' else None,
    )


def _items_response(batch, items):
    return Response({
        'success': True,
        'data': {
            'batch_id': str(batch.id),
            'items': GeneratedItemSerializer(items, many=True).data,
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_bundle(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    cost = settings.WALLET_COSTS['ai_generate_bundle']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    topic = request.data.get('topic', '') or request.data.get('goal', '')
    if not topic:
        return Response({'success': False, 'error': 'موضوع نمی‌تواند خالی باشد', 'code': 'EMPTY_TOPIC'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not settings.OPENAI_API_KEY:
        return Response({'success': False, 'error': 'کلید API هوش مصنوعی تنظیم نشده است', 'code': 'AI_NOT_CONFIGURED'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    batch = _create_generation_batch(workspace_id, request.user, 'bundle', 'text', request.data)

    platform = request.data.get('platform', '')
    result, error, tokens = openai_client.generate_bundle(
        topic=topic,
        platform=platform,
        tone=request.data.get('tone', 'حرفه‌ای'),
    )

    if error:
        batch.status = 'failed'
        batch.save()
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    items = []
    item_specs = [
        ('full_text', result['full_text']),
        ('short_text', result['short_text']),
        ('hashtags', '\n'.join(result['hashtags'])),
        ('title', result['title']),
    ]
    for order, (item_type, content) in enumerate(item_specs):
        items.append(GeneratedItem.objects.create(
            batch=batch,
            item_type=item_type,
            order=order,
            content=content
        ))

    batch.status = 'success'
    batch.wallet_cost_charged = cost
    batch.save()
    deduct_wallet(wallet, cost, f'بازتولید همزمان - {topic[:50]}')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            image_source = result.get('full_text') or result.get('title') or topic
            image_item, image_error = _generate_image_for_batch(batch, image_source, image_wallet, image_cost, platform=platform)
            if image_error:
                batch.image_status = 'failed'
                batch.save(update_fields=['image_status'])
            if image_item:
                items.append(image_item)

    return _items_response(batch, items)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_multi_variant(request, workspace_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    capability = request.data.get('capability', '')
    if capability not in {'text', 'rewrite', 'summary', 'scenario', 'title', 'hashtag', 'cta', 'idea'}:
        return Response({'success': False, 'error': 'قابلیت نامعتبر', 'code': 'INVALID_CAPABILITY'},
                        status=status.HTTP_400_BAD_REQUEST)

    try:
        variant_count = int(request.data.get('variant_count', 2))
    except (ValueError, TypeError):
        return Response({'success': False, 'error': 'تعداد نسخه باید ۲ یا ۳ باشد', 'code': 'INVALID_VARIANT_COUNT'},
                        status=status.HTTP_400_BAD_REQUEST)
    if variant_count not in (2, 3):
        return Response({'success': False, 'error': 'تعداد نسخه باید ۲ یا ۳ باشد', 'code': 'INVALID_VARIANT_COUNT'},
                        status=status.HTTP_400_BAD_REQUEST)

    cost_key = 'ai_generate_variant_2' if variant_count == 2 else 'ai_generate_variant_3'
    cost = settings.WALLET_COSTS[cost_key]
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    if not settings.OPENAI_API_KEY:
        return Response({'success': False, 'error': 'کلید API هوش مصنوعی تنظیم نشده است', 'code': 'AI_NOT_CONFIGURED'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    params = dict(request.data)
    params['variant_count'] = variant_count
    batch = _create_generation_batch(workspace_id, request.user, 'multi_variant', capability, params)

    variants, error, tokens = openai_client.generate_variants(capability, params, count=variant_count)

    if error:
        batch.status = 'failed'
        batch.save()
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    items = []
    for order, content in enumerate(variants):
        items.append(GeneratedItem.objects.create(
            batch=batch,
            item_type='variant',
            order=order + 1,
            content=content
        ))

    batch.status = 'success'
    batch.wallet_cost_charged = cost
    batch.save()
    deduct_wallet(wallet, cost, f'تولید چندگزینه‌ای {capability} - {variant_count} نسخه')

    if request.data.get('generate_image'):
        image_cost = settings.WALLET_COSTS['image_generation']
        image_wallet, image_err = check_wallet(workspace_id, image_cost)
        if not image_err:
            image_source = batch.topic
            image_item, image_error = _generate_image_for_batch(batch, image_source, image_wallet, image_cost, platform=batch.platform)
            if image_error:
                batch.image_status = 'failed'
                batch.save(update_fields=['image_status'])
            if image_item:
                items.append(image_item)

    return _items_response(batch, items)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_image_for_item(request, workspace_id, item_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        item = GeneratedItem.objects.get(
            id=item_id,
            batch__workspace_id=workspace_id,
            batch__user=request.user,
            batch__is_active=True
        )
    except GeneratedItem.DoesNotExist:
        return Response({'success': False, 'error': 'آیتم یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if item.item_type != 'variant':
        return Response({'success': False, 'error': 'فقط برای نسخه‌های چندگزینه‌ای قابل تولید مجدد است', 'code': 'INVALID_TYPE'},
                        status=status.HTTP_400_BAD_REQUEST)

    cost = settings.WALLET_COSTS['image_generation']
    wallet, err = check_wallet(workspace_id, cost)
    if err:
        return Response({'success': False, 'error': err, 'code': 'INSUFFICIENT_BALANCE'},
                        status=status.HTTP_402_PAYMENT_REQUIRED)

    image_item, image_error = _generate_image_for_batch(
        item.batch, item.content, wallet, cost, platform=item.batch.platform
    )
    if image_error:
        return Response({'success': False, 'error': image_error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({'success': True, 'data': GeneratedItemSerializer(image_item, context={'request': request}).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_generated_item(request, workspace_id, item_id):
    member = get_member(request.user, workspace_id)
    if not member:
        return Response({'success': False, 'error': 'دسترسی ندارید', 'code': 'FORBIDDEN'},
                        status=status.HTTP_403_FORBIDDEN)

    try:
        item = GeneratedItem.objects.get(
            id=item_id,
            batch__workspace_id=workspace_id,
            batch__user=request.user,
            batch__is_active=True
        )
    except GeneratedItem.DoesNotExist:
        return Response({'success': False, 'error': 'آیتم یافت نشد', 'code': 'NOT_FOUND'},
                        status=status.HTTP_404_NOT_FOUND)

    if item.saved_as_draft:
        return Response({'success': True, 'data': {'message': 'این آیتم قبلاً ذخیره شده است'}})

    title = request.data.get('title') or item.batch.topic[:100] or 'محتوای تولید شده'
    if item.item_type == 'title':
        title = item.content[:100]

    include_image = request.data.get('include_image', False)
    image = None
    if include_image:
        image = item.batch.items.filter(item_type='image').first()
        if not image:
            image = item.image if item.item_type == 'image' else None

    from content.models import Content
    content = Content.objects.create(
        workspace_id=workspace_id,
        created_by=request.user,
        title=title,
        body=item.content,
        status='draft',
        language='fa',
        goal=item.batch.topic[:300]
    )

    if image and image.image:
        content.image = image.image
        content.save(update_fields=['image'])

    item.saved_as_draft = True
    item.save()

    return Response({'success': True, 'data': {'content_id': str(content.id), 'message': 'در پیش‌نویس‌ها ذخیره شد'}})
