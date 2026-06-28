import random
import string
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, OTPCode
from .serializers import (
    OTPRequestSerializer, OTPVerifySerializer,
    UserSerializer, UserUpdateSerializer
)


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_sms(phone_number, code):
    from django.conf import settings
    print(f"[OTP] Phone: {phone_number}, Code: {code}")
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def otp_request(request):
    serializer = OTPRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': list(serializer.errors.values())[0][0],
            'code': 'VALIDATION_ERROR'
        }, status=status.HTTP_400_BAD_REQUEST)

    phone_number = serializer.validated_data['phone_number']

    OTPCode.objects.filter(
        phone_number=phone_number,
        is_used=False,
        expires_at__gt=timezone.now()
    ).update(is_used=True)

    code = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    OTPCode.objects.create(
        phone_number=phone_number,
        code=code,
        expires_at=expires_at
    )

    send_sms(phone_number, code)

    return Response({'success': True, 'data': {'message': 'کد ارسال شد'}})


@api_view(['POST'])
@permission_classes([AllowAny])
def otp_verify(request):
    serializer = OTPVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': list(serializer.errors.values())[0][0],
            'code': 'VALIDATION_ERROR'
        }, status=status.HTTP_400_BAD_REQUEST)

    phone_number = serializer.validated_data['phone_number']
    code = serializer.validated_data['code']

    otp = OTPCode.objects.filter(
        phone_number=phone_number,
        code=code,
        is_used=False,
        expires_at__gt=timezone.now()
    ).order_by('-created_at').first()

    if not otp:
        return Response({
            'success': False,
            'error': 'کد نامعتبر یا منقضی شده است',
            'code': 'INVALID_OTP'
        }, status=status.HTTP_400_BAD_REQUEST)

    otp.is_used = True
    otp.save()

    user, created = User.objects.get_or_create(phone_number=phone_number)

    refresh = RefreshToken.for_user(user)
    return Response({
        'success': True,
        'data': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'full_name': user.full_name,
            }
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    from rest_framework_simplejwt.serializers import TokenRefreshSerializer
    serializer = TokenRefreshSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': 'توکن نامعتبر است',
            'code': 'INVALID_TOKEN'
        }, status=status.HTTP_400_BAD_REQUEST)
    return Response({'success': True, 'data': serializer.validated_data})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_login(request):
    phone_number = request.data.get('phone_number', '').strip()
    password = request.data.get('password', '')

    if not phone_number or not password:
        return Response({
            'success': False,
            'error': 'شماره موبایل و رمز عبور الزامی است',
            'code': 'MISSING_FIELDS'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(phone_number=phone_number)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'error': 'شماره موبایل یا رمز عبور اشتباه است',
            'code': 'INVALID_CREDENTIALS'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):
        return Response({
            'success': False,
            'error': 'شماره موبایل یا رمز عبور اشتباه است',
            'code': 'INVALID_CREDENTIALS'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({
            'success': False,
            'error': 'حساب کاربری غیرفعال است',
            'code': 'ACCOUNT_DISABLED'
        }, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        'success': True,
        'data': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'phone_number': user.phone_number,
                'full_name': user.full_name,
            }
        }
    })


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'GET':
        serializer = UserSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})

    serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'error': list(serializer.errors.values())[0][0],
            'code': 'VALIDATION_ERROR'
        }, status=status.HTTP_400_BAD_REQUEST)
    serializer.save()
    return Response({'success': True, 'data': UserSerializer(request.user).data})
