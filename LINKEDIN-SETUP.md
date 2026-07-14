# راه‌اندازی اتصال LinkedIn

## متغیرهای محیطی

این مقادیر را در Secret Manager محیط اجرا یا فایل محلی `.env` قرار دهید؛ فایل `.env` نباید commit شود.

```env
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=https://YOUR_DOMAIN/api/auth/linkedin/callback/
LINKEDIN_TOKEN_ENCRYPTION_KEY=FERNET_KEY
LINKEDIN_API_VERSION=202604
LINKEDIN_ORG_ENABLED=false
CORS_ALLOWED_ORIGINS=https://YOUR_DOMAIN
CSRF_TRUSTED_ORIGINS=https://YOUR_DOMAIN
```

کلید Fernet را فقط یک‌بار بسازید، در Secret Manager نگه دارید و بدون برنامه rotation تغییر ندهید:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## چک‌لیست LinkedIn Developer Portal

1. در LinkedIn Developers یک App بسازید و آن را به Company Page معتبر متصل کنید.
2. در بخش Products، محصول **Sign In with LinkedIn using OpenID Connect** را فعال کنید.
3. محصول **Share on LinkedIn** را فعال کنید تا scope `w_member_social` در دسترس باشد.
4. در Auth > Authorized redirect URLs، مقدار دقیق `LINKEDIN_REDIRECT_URI` را ثبت کنید. مسیر، scheme، دامنه و slash پایانی باید دقیقاً یکسان باشند.
5. Client ID و Client Secret را در Secret Manager سرور قرار دهید؛ آن‌ها را در فرانت‌اند وارد نکنید.
6. migration را اجرا کنید: `.\.venv\Scripts\python.exe backend\manage.py migrate`.
7. سرویس backend و worker زمان‌بندی را restart کنید.
8. از صفحه «کانال‌ها»، LinkedIn را انتخاب و اتصال یک حساب آزمایشی را کامل کنید؛ سپس یک پست متنی و یک پست تصویری آزمایشی منتشر کنید.

## دسترسی‌های قابل استفاده

- پروفایل شخصی: `openid profile email w_member_social`. پس از فعال شدن دو Product بالا قابل آزمایش است.
- صفحه سازمانی: به `w_organization_social`، نقش معتبر در Page و معمولاً تأیید Community Management API نیاز دارد. این مسیر تا زمان دریافت دسترسی با `LINKEDIN_ORG_ENABLED=false` غیرفعال بماند.
- refresh token: فقط برای برنامه‌های تأییدشده Marketing Developer Platform صادر می‌شود. در نبود آن، رابط اتصال مجدد استفاده می‌شود.

## تصاویر راهنما

نسخه فعلی راهنما با کارت‌های مرحله‌ای و آیکن‌های داخلی کار می‌کند و به تصویر خارجی نیاز ندارد. اگر راهنمای اسکرین‌شاتی می‌خواهید، این سه تصویر را با حذف Client Secret، ایمیل و شناسه‌های حساس تهیه کنید:

1. صفحه Products برنامه LinkedIn با دو Product فعال.
2. بخش Authorized redirect URLs که فقط دامنه و callback را نشان دهد.
3. صفحه consent کاربر LinkedIn با نام برنامه و مجوز انتشار.

ابعاد پیشنهادی هر تصویر `1440×900` و فرمت WebP است.

## استقرار روی n8n.abrit.io

فایل‌های آماده استقرار این دامنه:

- `deploy/n8n.abrit.io.env.template`: قالب متغیرهای production؛ مقدارهای `CHANGE_ME` باید فقط روی VPS جایگزین شوند.
- `deploy/nginx-n8n.abrit.io.conf`: مسیر `/api/`، شامل callback لینکدین، را به Gunicorn می‌فرستد.
- `scripts/deploy-vps.sh`: نصب، build، migration، collectstatic، restart و health check را اجرا می‌کند.

روی VPS، پس از قرار دادن `.env` production، اجرا کنید:

```bash
cd /var/www/mohtavayar
bash scripts/deploy-vps.sh
```

تست callback بعد از deploy باید به‌جای 404 یک صفحه HTML با status 200 برگرداند:

```bash
curl -i "https://n8n.abrit.io/api/auth/linkedin/callback/?error=access_denied&error_description=test"
```
