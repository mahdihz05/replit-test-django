from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from users.models import User
from workspaces.models import Workspace, WorkspaceMember
from .models import Content, ContentVersion
from .views import content_list


class ContentListFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09127777777')
        self.workspace = Workspace.objects.create(name='تصاویر', owner=self.user)
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role='admin',
            added_by=self.user,
        )
        self.factory = APIRequestFactory()

    def test_can_filter_persisted_ai_images(self):
        ai_image = Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='AI image',
            image='content/images/ai.png',
        )
        ContentVersion.objects.create(content=ai_image, body='prompt', version_number=1, source='ai')

        user_image = Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='User image',
            image='content/images/user.png',
        )
        ContentVersion.objects.create(content=user_image, body='body', version_number=1, source='user')

        no_image = Content.objects.create(
            workspace=self.workspace,
            created_by=self.user,
            title='No image',
        )
        ContentVersion.objects.create(content=no_image, body='body', version_number=1, source='ai')

        request = self.factory.get('/contents/?has_image=true&source=ai')
        force_authenticate(request, user=self.user)
        response = content_list(request, self.workspace.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.data['data']], [str(ai_image.id)])
