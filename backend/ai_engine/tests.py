from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import User
from workspaces.models import Workspace, WorkspaceMember

from config.ai import (
    apply_profit_margin,
    calculate_image_operation_cost_irt,
    calculate_text_operation_cost_irt,
    get_model,
    get_wallet_cost,
)
from .models import AIConfiguration, GeneratedItem, GenerationBatch
from .prompts import build_image_prompt_from_text, build_text_prompt


class AIConfigurationTests(TestCase):
    def setUp(self):
        self.configuration, _ = AIConfiguration.objects.get_or_create(pk=1)

    def test_default_models_and_wallet_costs(self):
        self.assertEqual(get_model('chat'), 'gpt-5-mini')
        self.assertEqual(get_model('title_suggestions'), 'gpt-5-nano')
        self.assertEqual(get_model('image_generation'), 'gpt-image-1.5')
        self.assertEqual(get_wallet_cost('image_generation'), 9800)

    def test_admin_values_override_defaults_immediately(self):
        costs = dict(self.configuration.wallet_costs)
        costs['text_generation'] = 777
        models = dict(self.configuration.ai_models)
        models['chat'] = 'custom-chat-model'
        self.configuration.wallet_costs = costs
        self.configuration.ai_models = models
        self.configuration.save()

        self.assertEqual(get_wallet_cost('text_generation'), 777)
        self.assertEqual(get_model('chat'), 'custom-chat-model')

    def test_raw_cost_calculations(self):
        self.assertEqual(calculate_text_operation_cost_irt('text_generation'), 486)
        self.assertEqual(calculate_image_operation_cost_irt('medium'), 6120)
        self.assertEqual(apply_profit_margin(6120), 9790)


class ImageGenerationTests(TestCase):
    @override_settings(OPENAI_API_KEY='test-key')
    @patch('ai_engine.openai_client._save_image_from_base64', return_value='content/images/test.png')
    @patch('ai_engine.openai_client.get_openai_client')
    def test_gpt_image_defaults_and_base64_response(self, get_client, save_image):
        image_api = Mock()
        image_api.generate.return_value = SimpleNamespace(
            data=[SimpleNamespace(b64_json='aW1hZ2U=', url=None)]
        )
        get_client.return_value = SimpleNamespace(images=image_api)

        from .openai_client import generate_image

        path, error = generate_image('a test image')

        self.assertIsNone(error)
        self.assertEqual(path, 'content/images/test.png')
        image_api.generate.assert_called_once()
        call = image_api.generate.call_args.kwargs
        self.assertEqual(call['model'], 'gpt-image-1.5')
        self.assertTrue(call['prompt'].startswith('a test image'))
        self.assertEqual(call['size'], '1024x1024')
        self.assertEqual(call['quality'], 'medium')
        self.assertNotIn('response_format', call)
        self.assertEqual(call['output_format'], 'png')
        self.assertEqual(call['n'], 1)
        save_image.assert_called_once_with('aW1hZ2U=')

    def test_editorial_image_prompt_is_detailed_and_avoids_stock_ai_cliches(self):
        prompt = build_image_prompt_from_text('هوشمند شدن کسب و کار با مثال کداک', 'telegram')

        self.assertIn('production-ready English prompt', prompt)
        self.assertIn('meaningful metaphor', prompt)
        self.assertIn("person using a laptop", prompt)
        self.assertIn('floating holographic interface', prompt)
        self.assertIn('square editorial visual', prompt)
        self.assertIn('no extra explanation', prompt)


class ContentPromptQualityTests(TestCase):
    def test_text_prompt_forbids_echoing_user_request(self):
        request = 'ضرورت هوشمند شدن کسب و کارها را توضیح بده'
        _, prompt = build_text_prompt(request, 'telegram', 'حرفه‌ای', '', 'fa', 300)

        self.assertIn(f'<user_request>\n{request}\n</user_request>', prompt)
        self.assertIn('NEVER quote, echo, summarize, or mention the request itself', prompt)
        self.assertIn("Start with the actual publishable hook", prompt)
        self.assertIn('factual plausibility', prompt)


class GeneratedItemDraftTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000009')
        self.workspace = Workspace.objects.create(name='AI draft test', owner=self.user)
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.user,
            role='admin',
            added_by=self.user,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.batch = GenerationBatch.objects.create(
            workspace=self.workspace,
            user=self.user,
            mode='bundle',
            capability='text',
            topic='موضوع داخلی',
            platform='linkedin',
            status='success',
        )
        self.full_body = '\n'.join(
            [f'بند کامل شماره {index}: متن آماده انتشار لینکدین.' for index in range(1, 31)]
        )
        self.item = GeneratedItem.objects.create(
            batch=self.batch,
            item_type='full_text',
            content=self.full_body,
        )
        self.url = f'/api/workspaces/{self.workspace.id}/ai/generate/items/{self.item.id}/save/'

    def test_saved_item_keeps_full_body_and_returns_same_content_on_repeat(self):
        first = self.client.post(self.url, {}, format='json')
        self.assertEqual(first.status_code, 200)
        content_id = first.data['data']['content_id']

        self.item.refresh_from_db()
        self.assertEqual(str(self.item.saved_content_id), content_id)
        self.assertEqual(self.item.saved_content.body, self.full_body)
        self.assertEqual(len(self.item.saved_content.body.splitlines()), 30)

        second = self.client.post(self.url, {}, format='json')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.data['data']['content_id'], content_id)
