from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from config.ai import (
    apply_profit_margin,
    calculate_image_operation_cost_irt,
    calculate_text_operation_cost_irt,
    get_model,
    get_wallet_cost,
)
from .models import AIConfiguration


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
        self.assertEqual(call['response_format'], 'b64_json')
        self.assertEqual(call['output_format'], 'png')
        self.assertEqual(call['n'], 1)
        save_image.assert_called_once_with('aW1hZ2U=')
