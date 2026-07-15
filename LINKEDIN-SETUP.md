# راه‌اندازی اتصال LinkedIn

## متغیرهای محیطی

این مقادیر را در Secret Manager محیط اجرا یا فایل محلی `.env` قرار دهید؛ فایل `.env` نباید commit شود.

```env
LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_REDIRECT_URI=https://YOUR_DOMAIN/api/auth/linkedin/callback/
LINKEDIN_TOKEN_ENCRYPTION_KEY=FERNET_KEY
LINKEDIN_API_VERSION=202606
LINKEDIN_ORG_ENABLED=false
CORS_ALLOWED_ORIGINS=https://YOUR_DOMAIN
CSRF_TRUSTED_ORIGINS=https://YOUR_DOMAIN
```

کلید Fernet را فقط یک‌بار بسازید، در Secret Manager نگه دارید و بدون برنامه rotation تغییر ندهید:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## تست کامل روی کامپیوتر لوکال (Windows)

LinkedIn برای OAuth وب، Callback مطلق **HTTPS** می‌خواهد. به همین دلیل `http://localhost:5173/...` را در Developer Portal ثبت نکنید. اسکریپت پروژه Frontend و Backend را با HTTPS توسعه اجرا می‌کند، یک گواهی self-signed محلی در `.runtime/certs` می‌سازد، Callback دقیق را در `.env` قرار می‌دهد و Backend را با تنظیم جدید restart می‌کند.

### اجرای بار اول

1. یک PowerShell باز کنید و از ریشه پروژه اجرا کنید:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\start-linkedin-local.ps1
   ```

2. خروجی دو آدرس می‌دهد:

   - `APP_URL`: برنامه را فقط از همین آدرس HTTPS باز کنید، نه از HTTP.
   - `LINKEDIN_CALLBACK`: این مقدار را کامل کپی کنید.

3. بار اول `APP_URL` را در مرورگر باز کنید. چون گواهی فقط برای توسعه ساخته شده، در صفحه هشدار `Advanced > Proceed to localhost` را بزنید.
4. وارد [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps) شوید، App را باز کنید و در `Auth > OAuth 2.0 settings > Authorized redirect URLs for your app` مقدار `LINKEDIN_CALLBACK` را اضافه و ذخیره کنید.
5. در `Products` وضعیت دو محصول زیر باید `Added` یا `Approved` باشد:

   - `Sign In with LinkedIn using OpenID Connect`
   - `Share on LinkedIn`

6. از `APP_URL` وارد محتوایار شوید و مسیر `کانال‌ها > افزودن کانال > LinkedIn` را باز کنید. راهنما باید وضعیت «آماده اتصال» و همان Callback را نشان دهد.
7. `پروفایل شخصی` را انتخاب کنید، روی اتصال بزنید، در دامنه رسمی `linkedin.com` وارد شوید و مجوزها را تأیید کنید.
8. پس از بسته‌شدن خودکار پنجره، یک پست متنی آزمایشی برای همان کانال منتشر کنید.

### نکات HTTPS لوکال

- Callback لوکال ثابت است: `https://localhost:5173/api/auth/linkedin/callback/`.
- گواهی self-signed فقط برای توسعه است. در Production حتماً از دامنه خودتان و TLS معتبر استفاده کنید.
- تا پایان تست، پردازش‌های ساخته‌شده را در حال اجرا نگه دارید.
- برای توقف فقط پردازش‌های مدیریت‌شده این تست اجرا کنید:

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\scripts\stop-linkedin-local.ps1
  ```

- لاگ‌ها در پوشه `.runtime` هستند. در صورت خطا ابتدا فایل‌های `linkedin-backend.err.log` و `linkedin-frontend.err.log` را بررسی کنید.
- اگر LinkedIn خطای `redirect_uri doesn’t match` داد، scheme، دامنه، مسیر و `/` پایانی Callback ثبت‌شده را با مقدار داخل مودال حرف‌به‌حرف مقایسه کنید.
- اگر مجوز `w_member_social` نمایش داده نشد، محصول `Share on LinkedIn` هنوز برای App فعال نشده است.

## چک‌لیست LinkedIn Developer Portal

1. در LinkedIn Developers یک App بسازید و آن را به Company Page معتبر متصل کنید.
2. در بخش Products، محصول **Sign In with LinkedIn using OpenID Connect** را فعال کنید.
3. محصول **Share on LinkedIn** را فعال کنید تا scope `w_member_social` در دسترس باشد.
4. در Auth > Authorized redirect URLs، مقدار دقیق `LINKEDIN_REDIRECT_URI` را ثبت کنید. scheme، دامنه، مسیر و slash پایانی باید دقیقاً یکسان باشند.
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
