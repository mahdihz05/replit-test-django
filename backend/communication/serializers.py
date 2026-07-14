from rest_framework import serializers

from .models import Campaign, CampaignMessage, CommunicationProvider, Contact, ContactGroup, ImportJob, MessageTemplate
from .services.imports import validate_contact_data
from .services.templates import extract_variables, sanitize_email_html


class CommunicationProviderSerializer(serializers.ModelSerializer):
    credentials = serializers.JSONField(write_only=True, required=False)
    has_credentials = serializers.SerializerMethodField()

    class Meta:
        model = CommunicationProvider
        fields = [
            'id', 'type', 'provider_key', 'name', 'credentials', 'has_credentials', 'settings', 'status',
            'last_tested_at', 'last_test_status', 'last_test_error', 'created_at', 'updated_at',
        ]
        read_only_fields = ['last_tested_at', 'last_test_status', 'last_test_error', 'created_at', 'updated_at']

    def get_has_credentials(self, obj):
        return bool(obj.encrypted_credentials)

    def validate(self, attrs):
        key = attrs.get('provider_key', getattr(self.instance, 'provider_key', ''))
        provider_type = attrs.get('type', getattr(self.instance, 'type', ''))
        expected = 'sms' if key == 'kavenegar' else 'email'
        if provider_type and provider_type != expected:
            raise serializers.ValidationError('نوع Provider با سرویس انتخابی سازگار نیست')
        if not self.instance and not attrs.get('credentials'):
            raise serializers.ValidationError({'credentials': 'اطلاعات اتصال الزامی است'})
        settings_data = attrs.get('settings', getattr(self.instance, 'settings', {})) or {}
        if key in ('gmail_smtp', 'custom_smtp'):
            if not settings_data.get('host') or not settings_data.get('port'):
                raise serializers.ValidationError({'settings': 'SMTP Host و Port الزامی هستند'})
            if settings_data.get('encryption', 'tls') not in ('ssl', 'tls', 'none'):
                raise serializers.ValidationError({'settings': 'نوع رمزنگاری SMTP نامعتبر است'})
        return attrs

    def create(self, validated_data):
        credentials = validated_data.pop('credentials', {})
        provider = CommunicationProvider(**validated_data)
        provider.set_credentials(credentials)
        provider.save()
        return provider

    def update(self, instance, validated_data):
        credentials = validated_data.pop('credentials', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if credentials:
            merged = instance.get_credentials()
            merged.update(credentials)
            instance.set_credentials(merged)
        instance.last_test_status = 'not_tested'
        instance.last_test_error = ''
        instance.save()
        return instance


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'name', 'phone', 'email', 'company', 'city', 'tags', 'custom_fields', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        data = {
            'phone': getattr(self.instance, 'phone', ''),
            'email': getattr(self.instance, 'email', ''),
            **dict(attrs),
        }
        errors = validate_contact_data(data)
        if errors:
            raise serializers.ValidationError(errors)
        if 'phone' in attrs or not self.instance:
            attrs['phone'] = data['phone']
        if 'email' in attrs or not self.instance:
            attrs['email'] = data['email']
        workspace = self.context.get('workspace')
        if workspace:
            queryset = Contact.objects.filter(workspace=workspace)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if attrs['phone'] and queryset.filter(phone=attrs['phone']).exists():
                raise serializers.ValidationError({'phone': 'این شماره قبلاً ثبت شده است'})
            if attrs['email'] and queryset.filter(email=attrs['email']).exists():
                raise serializers.ValidationError({'email': 'این ایمیل قبلاً ثبت شده است'})
        return attrs


class ContactGroupSerializer(serializers.ModelSerializer):
    contact_count = serializers.IntegerField(read_only=True)
    contact_ids = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.none(), many=True, write_only=True, required=False)

    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'description', 'contact_count', 'contact_ids', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workspace = self.context.get('workspace')
        if workspace:
            self.fields['contact_ids'].queryset = Contact.objects.filter(workspace=workspace)

    def create(self, validated_data):
        contacts = validated_data.pop('contact_ids', [])
        group = super().create(validated_data)
        group.contacts.set(contacts)
        return group

    def update(self, instance, validated_data):
        contacts = validated_data.pop('contact_ids', None)
        group = super().update(instance, validated_data)
        if contacts is not None:
            group.contacts.set(contacts)
        return group


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = ['id', 'channel', 'title', 'category', 'subject', 'body', 'body_type', 'variables', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        channel = attrs.get('channel', getattr(self.instance, 'channel', 'sms'))
        if channel == 'email' and not attrs.get('subject', getattr(self.instance, 'subject', '')):
            raise serializers.ValidationError({'subject': 'موضوع ایمیل الزامی است'})
        body = attrs.get('body', getattr(self.instance, 'body', ''))
        subject = attrs.get('subject', getattr(self.instance, 'subject', ''))
        if '\n' in subject or '\r' in subject:
            raise serializers.ValidationError({'subject': 'موضوع ایمیل نمی‌تواند چندخطی باشد'})
        body_type = attrs.get('body_type', getattr(self.instance, 'body_type', 'plain_text'))
        if channel == 'email' and body_type == 'html':
            attrs['body'] = sanitize_email_html(body)
            body = attrs['body']
        attrs['variables'] = extract_variables(subject, body)
        return attrs


class CampaignSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.name', read_only=True)
    selected_contact_ids = serializers.PrimaryKeyRelatedField(queryset=Contact.objects.none(), many=True, source='selected_contacts', write_only=True, required=False)
    selected_group_ids = serializers.PrimaryKeyRelatedField(queryset=ContactGroup.objects.none(), many=True, source='selected_groups', write_only=True, required=False)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'provider', 'provider_name', 'channel', 'name', 'status', 'template', 'subject', 'body',
            'body_type', 'selected_contact_ids', 'selected_group_ids', 'recipients_count', 'valid_recipients_count',
            'invalid_recipients_count', 'sent_count', 'failed_count', 'delivered_count', 'skipped_count',
            'success_rate', 'started_at', 'scheduled_at', 'finished_at', 'settings', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'status', 'recipients_count', 'valid_recipients_count', 'invalid_recipients_count', 'sent_count',
            'failed_count', 'delivered_count', 'skipped_count', 'started_at', 'scheduled_at', 'finished_at', 'created_at', 'updated_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workspace = self.context.get('workspace')
        if workspace:
            self.fields['provider'].queryset = CommunicationProvider.objects.filter(workspace=workspace, status='active')
            self.fields['template'].queryset = MessageTemplate.objects.filter(workspace=workspace)
            self.fields['selected_contact_ids'].queryset = Contact.objects.filter(workspace=workspace)
            self.fields['selected_group_ids'].queryset = ContactGroup.objects.filter(workspace=workspace)

    def get_success_rate(self, obj):
        return round((obj.sent_count / obj.valid_recipients_count) * 100, 1) if obj.valid_recipients_count else 0

    def validate(self, attrs):
        provider = attrs.get('provider', getattr(self.instance, 'provider', None))
        channel = attrs.get('channel', getattr(self.instance, 'channel', ''))
        if provider and provider.type != channel:
            raise serializers.ValidationError({'provider': 'Provider با نوع کمپین سازگار نیست'})
        if channel == 'email' and not attrs.get('subject', getattr(self.instance, 'subject', '')):
            raise serializers.ValidationError({'subject': 'موضوع ایمیل الزامی است'})
        subject = attrs.get('subject', getattr(self.instance, 'subject', ''))
        if '\n' in subject or '\r' in subject:
            raise serializers.ValidationError({'subject': 'موضوع ایمیل نمی‌تواند چندخطی باشد'})
        body_type = attrs.get('body_type', getattr(self.instance, 'body_type', 'plain_text'))
        if channel == 'email' and body_type == 'html':
            attrs['body'] = sanitize_email_html(attrs.get('body', getattr(self.instance, 'body', '')))
        return attrs

    def create(self, validated_data):
        contacts = validated_data.pop('selected_contacts', [])
        groups = validated_data.pop('selected_groups', [])
        campaign = super().create(validated_data)
        campaign.selected_contacts.set(contacts)
        campaign.selected_groups.set(groups)
        return campaign

    def update(self, instance, validated_data):
        contacts = validated_data.pop('selected_contacts', None)
        groups = validated_data.pop('selected_groups', None)
        campaign = super().update(instance, validated_data)
        if contacts is not None:
            campaign.selected_contacts.set(contacts)
        if groups is not None:
            campaign.selected_groups.set(groups)
        return campaign


class CampaignMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignMessage
        fields = [
            'id', 'recipient_name', 'recipient_phone', 'recipient_email', 'rendered_subject', 'rendered_body',
            'status', 'provider_message_id', 'provider_response', 'error_message', 'retry_count', 'is_test',
            'queued_at', 'sent_at', 'delivered_at', 'failed_at', 'created_at',
        ]


class ImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = ['id', 'file_name', 'file_type', 'status', 'total_rows', 'valid_rows', 'invalid_rows', 'duplicate_rows', 'mapping', 'errors', 'preview', 'created_at']
