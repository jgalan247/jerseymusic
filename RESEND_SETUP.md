# Resend Email Setup Guide

This guide explains how to configure Resend for email delivery in Jersey Events.

## Why Resend?

Resend is a modern email API designed for developers:
- **Simple API**: Easy to integrate and use
- **Great deliverability**: Optimized for transactional emails
- **Developer-friendly**: Built-in testing, webhooks, and analytics
- **Affordable**: Generous free tier (100 emails/day, 3,000/month)

## Setup Steps

### 1. Create a Resend Account

1. Go to [resend.com](https://resend.com)
2. Sign up for a free account
3. Verify your email address

### 2. Get Your API Key

1. Log into your Resend dashboard
2. Navigate to **API Keys** in the sidebar
3. Click **Create API Key**
4. Give it a name (e.g., "Jersey Events Production")
5. Select permissions: **Sending access**
6. Copy the API key (starts with `re_`)

**IMPORTANT**: Save this key securely! You won't be able to see it again.

### 3. Configure Domain (Production) or Use Test Domain

#### Option A: Use Test Domain (Quick Start)

For testing, Resend provides `onboarding@resend.dev` which works immediately:

```bash
# In your Railway/production environment variables
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_api_key_here
DEFAULT_FROM_EMAIL=Jersey Events <onboarding@resend.dev>
```

**Note**: Test domain has limitations:
- Can only send to your verified email address
- Has "via resend.dev" in email headers
- Not suitable for production with real users

#### Option B: Verify Your Custom Domain (Recommended for Production)

1. In Resend dashboard, go to **Domains**
2. Click **Add Domain**
3. Enter your domain (e.g., `coderra.je`)
4. Add the DNS records shown to your domain's DNS settings:
   - **SPF** record (TXT)
   - **DKIM** records (CNAME)
   - **DMARC** record (TXT) - optional but recommended

5. Wait for verification (usually 5-10 minutes)
6. Once verified, you can send from any email address on your domain

```bash
# In your Railway/production environment variables
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_api_key_here
DEFAULT_FROM_EMAIL=Jersey Events <noreply@coderra.je>
```

### 4. Set Environment Variables in Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Navigate to **Variables** tab
4. Add these variables:

```bash
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_actual_api_key_here
```

5. Optionally override the default from email:
```bash
DEFAULT_FROM_EMAIL=Jersey Events <noreply@coderra.je>
```

6. Deploy your changes

### 5. Test Email Sending

After deployment, test the email verification:

1. Register a new account using your personal email
2. Check your inbox for the verification email
3. If you don't receive it, check:
   - Railway logs for errors
   - Resend dashboard > **Emails** to see sent emails
   - Spam folder

## Monitoring & Debugging

### Check Resend Dashboard

1. Go to [resend.com](https://resend.com) and log in
2. Click **Emails** in the sidebar
3. You'll see all sent emails with status:
   - ✅ **Delivered**: Email was successfully delivered
   - ⏳ **Queued**: Email is being processed
   - ❌ **Failed**: Check error message

### Check Railway Logs

```bash
# View live logs
railway logs

# Look for email-related messages
railway logs | grep "📧"
```

### Common Issues

#### 1. "RESEND_API_KEY not configured"
- Make sure you added `RESEND_API_KEY` to Railway environment variables
- Restart your Railway service after adding variables

#### 2. "Email not received"
- Check Resend dashboard to see if email was sent
- Verify you're using the correct "from" email:
  - Test: `onboarding@resend.dev`
  - Production: Your verified domain email
- Check spam folder
- If using test domain, make sure recipient email is the one you verified with Resend

#### 3. "Domain not verified"
If using custom domain (`noreply@coderra.je`), verify DNS records are correct:
```bash
# Check DNS records
dig TXT coderra.je
dig CNAME resend._domainkey.coderra.je
```

#### 4. Rate Limits
Free tier limits:
- 100 emails per day
- 3,000 emails per month
- If exceeded, emails will fail with rate limit error

## Environment Variable Summary

```bash
# Required
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxxx

# Optional (has defaults)
DEFAULT_FROM_EMAIL=Jersey Events <noreply@coderra.je>
DEBUG=False  # Must be False for production email
```

## Testing Locally

To test Resend locally:

1. Create a `.env` file in project root:
```bash
DEBUG=False  # Must be False to use production email
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxxx
DEFAULT_FROM_EMAIL=Jersey Events <onboarding@resend.dev>
LOCAL_TEST=True
```

2. Run Django:
```bash
python manage.py runserver
```

3. Register an account and check email delivery

## Cost

Resend pricing (as of 2024):
- **Free**: 3,000 emails/month, 100/day
- **Pro**: $20/month for 50,000 emails, then $1 per 1,000
- **Enterprise**: Custom pricing

For Jersey Events usage:
- Verification emails: ~1 per new user
- Order confirmations: ~1-2 per order
- With 100 new users/month: Well within free tier

## Support

- Resend Documentation: [resend.com/docs](https://resend.com/docs)
- Resend Python SDK: [github.com/resendlabs/resend-python](https://github.com/resendlabs/resend-python)
- Jersey Events Issues: [GitHub Issues](https://github.com/yourusername/jerseymusic/issues)
