from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from workspaces.models import WorkspaceMember
from wallet.models import Wallet, WalletTransaction
from django.conf import settings

from .models import AIChatSession, AIChatMessage
from .serializers import AIChatSessionSerializer, AIChatSessionListSerializer, AIChatMessageSerializer
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
        metadata={'tokens': tokens, 'model': 'gpt-4o'}
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
    result, error, tokens = openai_client.generate_text(
        goal=goal,
        platform=request.data.get('platform', ''),
        tone=request.data.get('tone', 'حرفه‌ای'),
        keywords=request.data.get('keywords', ''),
        language=request.data.get('language', 'fa'),
        word_count=request.data.get('word_count', 300)
    )

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'تولید متن - {goal[:50]}')
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
    result, error = openai_client.generate_image(
        description=description,
        style=request.data.get('style', '')
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
    result, error, tokens = openai_client.rewrite_text(text, request.data.get('tone', 'حرفه‌ای'))

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, 'بازنویسی متن')
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
    result, error, tokens = openai_client.suggest_titles(topic)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'پیشنهاد عنوان - {topic[:50]}')
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
    result, error, tokens = openai_client.suggest_hashtags(topic)

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'پیشنهاد هشتگ - {topic[:50]}')
    return Response({'success': True, 'data': {'hashtags': result}})


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
    result, error, tokens = openai_client.generate_cta(goal, request.data.get('platform', ''))

    if error:
        return Response({'success': False, 'error': error, 'code': 'AI_ERROR'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE)

    deduct_wallet(wallet, cost, f'تولید CTA - {goal[:50]}')
    return Response({'success': True, 'data': {'ctas': result}})
