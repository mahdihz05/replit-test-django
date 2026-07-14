"""Central AI model and pricing configuration.

The constants in this module are safe defaults.  When Django is running and an
AIConfiguration row exists, the getters below overlay the admin-managed values
without making migrations or management commands depend on the database being
available at import time.
"""

from copy import deepcopy
from decimal import Decimal

from django.apps import apps
from django.db import OperationalError, ProgrammingError


USD_TO_IRT = 180_000
PROFIT_MULTIPLIER = 1.6
MINIMUM_OPERATION_COST = 25

AI_MODELS = {
    "chat": "gpt-5-mini",
    "text_generation": "gpt-5-mini",
    "content_generation": "gpt-5-mini",
    "content_rewrite": "gpt-5-mini",
    "title_suggestions": "gpt-5-nano",
    "hashtag_suggestions": "gpt-5-nano",
    "cta_generation": "gpt-5-nano",
    "image_generation": "gpt-image-1.5",
    "sms_ai_generate": "gpt-5-nano",
    "sms_ai_rewrite": "gpt-5-mini",
    "sms_ai_shorten": "gpt-5-nano",
    "email_subject_generate": "gpt-5-nano",
    "email_body_generate": "gpt-5-mini",
    "email_ai_rewrite": "gpt-5-mini",
    "campaign_ai_generate_bundle": "gpt-5-mini",
}

MODEL_PRICING_USD = {
    "gpt-5-mini": {
        "input_per_1m_tokens": 0.25,
        "output_per_1m_tokens": 2.00,
    },
    "gpt-5-nano": {
        "input_per_1m_tokens": 0.05,
        "output_per_1m_tokens": 0.40,
    },
    "gpt-image-1.5": {
        "image_1024x1024_low": 0.009,
        "image_1024x1024_medium": 0.034,
        "image_1024x1024_high": 0.133,
    },
}

ESTIMATED_TOKEN_USAGE = {
    "text_generation": {"input_tokens": 1200, "output_tokens": 1200, "model": "gpt-5-mini"},
    "content_rewrite": {"input_tokens": 1200, "output_tokens": 700, "model": "gpt-5-mini"},
    "title_suggestions": {"input_tokens": 400, "output_tokens": 120, "model": "gpt-5-nano"},
    "hashtag_suggestions": {"input_tokens": 400, "output_tokens": 120, "model": "gpt-5-nano"},
    "cta_generation": {"input_tokens": 400, "output_tokens": 150, "model": "gpt-5-nano"},
    "ai_generate_variant_2": {"input_tokens": 1400, "output_tokens": 1600, "model": "gpt-5-mini"},
    "ai_generate_variant_3": {"input_tokens": 1600, "output_tokens": 2400, "model": "gpt-5-mini"},
    "ai_generate_bundle": {"input_tokens": 2200, "output_tokens": 3200, "model": "gpt-5-mini"},
    "sms_ai_generate": {"input_tokens": 500, "output_tokens": 250, "model": "gpt-5-nano"},
    "sms_ai_rewrite": {"input_tokens": 700, "output_tokens": 300, "model": "gpt-5-mini"},
    "sms_ai_shorten": {"input_tokens": 500, "output_tokens": 150, "model": "gpt-5-nano"},
    "email_subject_generate": {"input_tokens": 500, "output_tokens": 150, "model": "gpt-5-nano"},
    "email_body_generate": {"input_tokens": 1000, "output_tokens": 1200, "model": "gpt-5-mini"},
    "email_ai_rewrite": {"input_tokens": 1200, "output_tokens": 900, "model": "gpt-5-mini"},
    "campaign_ai_generate_bundle": {"input_tokens": 1800, "output_tokens": 2400, "model": "gpt-5-mini"},
}

WALLET_COSTS = {
    "text_generation": 500,
    "image_generation": 9800,
    "content_rewrite": 350,
    "title_suggestions": 30,
    "hashtag_suggestions": 30,
    "cta_generation": 40,
    "ai_generate_bundle": 1800,
    "ai_generate_variant_2": 1100,
    "ai_generate_variant_3": 1600,
    "sms_ai_generate": 40,
    "sms_ai_rewrite": 350,
    "sms_ai_shorten": 30,
    "email_subject_generate": 30,
    "email_body_generate": 500,
    "email_ai_rewrite": 350,
    "campaign_ai_generate_bundle": 1800,
}

IMAGE_GENERATION_DEFAULTS = {
    "model": "gpt-image-1.5",
    "size": "1024x1024",
    "quality": "medium",
}

IMAGE_WALLET_COSTS = {"low": 2600, "medium": 9800, "high": 38300}

IMAGE_QUALITY_BY_PLAN = {
    "free": "low",
    "basic": "low",
    "pro": "medium",
    "business": "high",
}

AI_CONFIG = {
    "usd_to_irt": USD_TO_IRT,
    "profit_multiplier": PROFIT_MULTIPLIER,
    "minimum_operation_cost": MINIMUM_OPERATION_COST,
    "models": AI_MODELS,
    "model_pricing_usd": MODEL_PRICING_USD,
    "estimated_token_usage": ESTIMATED_TOKEN_USAGE,
    "wallet_costs": WALLET_COSTS,
    "image_defaults": IMAGE_GENERATION_DEFAULTS,
    "image_wallet_costs": IMAGE_WALLET_COSTS,
}


def _database_overrides():
    """Return admin overrides, or an empty mapping before/unavailable DB setup."""
    try:
        if not apps.ready:
            return {}
        configuration_model = apps.get_model("ai_engine", "AIConfiguration")
        configuration = configuration_model.objects.order_by("pk").first()
        if not configuration:
            return {}
        return {
            "usd_to_irt": configuration.usd_to_irt,
            "profit_multiplier": float(configuration.profit_multiplier),
            "minimum_operation_cost": configuration.minimum_operation_cost,
            "models": configuration.ai_models,
            "model_pricing_usd": configuration.model_pricing_usd,
            "estimated_token_usage": configuration.estimated_token_usage,
            "wallet_costs": configuration.wallet_costs,
            "image_defaults": configuration.image_defaults,
            "image_wallet_costs": configuration.image_wallet_costs,
        }
    except (LookupError, OperationalError, ProgrammingError):
        return {}


def get_ai_config():
    config = deepcopy(AI_CONFIG)
    for key, value in _database_overrides().items():
        if value not in (None, {}):
            if isinstance(config.get(key), dict) and isinstance(value, dict):
                config[key].update(deepcopy(value))
            else:
                config[key] = deepcopy(value)
    return config


def get_model(operation_name):
    config = get_ai_config()
    models = config["models"]
    if operation_name in models:
        return models[operation_name]
    usage = config["estimated_token_usage"].get(operation_name, {})
    return usage.get("model", models["content_generation"])


def get_wallet_cost(operation_name):
    return int(get_ai_config()["wallet_costs"][operation_name])


def get_image_defaults():
    config = get_ai_config()
    defaults = config["image_defaults"]
    quality = defaults.get("quality", "medium")
    return {
        "model": defaults.get("model", config["models"]["image_generation"]),
        "size": defaults.get("size", "1024x1024"),
        "quality": quality,
    }


def calculate_text_operation_cost_irt(operation_name):
    config = get_ai_config()
    usage = config["estimated_token_usage"][operation_name]
    pricing = config["model_pricing_usd"][usage["model"]]
    input_cost = Decimal(str(usage["input_tokens"])) / Decimal(1_000_000)
    input_cost *= Decimal(str(pricing["input_per_1m_tokens"]))
    output_cost = Decimal(str(usage["output_tokens"])) / Decimal(1_000_000)
    output_cost *= Decimal(str(pricing["output_per_1m_tokens"]))
    return round((input_cost + output_cost) * Decimal(config["usd_to_irt"]))


def calculate_image_operation_cost_irt(quality="medium"):
    config = get_ai_config()
    defaults = config["image_defaults"]
    model = defaults.get("model", config["models"]["image_generation"])
    size = defaults.get("size", "1024x1024")
    price_key = f"image_{size}_{quality}"
    price = Decimal(str(config["model_pricing_usd"][model][price_key]))
    return round(price * Decimal(config["usd_to_irt"]))


def apply_profit_margin(raw_cost_irt):
    config = get_ai_config()
    final_cost = Decimal(raw_cost_irt) * Decimal(str(config["profit_multiplier"]))
    final_cost = max(final_cost, Decimal(config["minimum_operation_cost"]))
    return int(round(final_cost / Decimal(10)) * 10)
