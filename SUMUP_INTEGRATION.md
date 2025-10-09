# SumUp Integration Setup

## Overview
The SumUp payment integration has been fully configured for the Jersey Events platform with proper environment variables and Django endpoints.

## Ngrok Configuration
- **Base URL**: https://86a7ab44d9e2.ngrok-free.app
- All endpoints are configured to use full URLs for webhooks and callbacks

## Environment Variables (.env)
```bash
# SumUp API Configuration
SUMUP_BASE_URL=https://api.sumup.com
SUMUP_API_URL=https://api.sumup.com/v0.1
SUMUP_API_BASE_URL=https://api.sandbox.sumup.com

# SumUp OAuth Credentials
SUMUP_CLIENT_ID=cc_classic_7MYt7JuELKZUqp4FXOjbga44CIS0v
SUMUP_CLIENT_SECRET=c_sk_classic_VAVIadfYRlm3ZkzEC6YU5TYVNWf39VeZdEUA6RnfW7E7DwEcu6

# Callback URLs (using full ngrok URLs)
SUMUP_REDIRECT_URI=https://86a7ab44d9e2.ngrok-free.app/payments/sumup/oauth/callback/
SUMUP_WEBHOOK_URL=https://86a7ab44d9e2.ngrok-free.app/payments/sumup/webhook/
SUMUP_SUCCESS_URL=https://86a7ab44d9e2.ngrok-free.app/payments/success/
SUMUP_FAIL_URL=https://86a7ab44d9e2.ngrok-free.app/payments/fail/
SUMUP_CANCEL_URL=https://86a7ab44d9e2.ngrok-free.app/payments/cancel/

# Site Configuration
SITE_URL=https://86a7ab44d9e2.ngrok-free.app
```

## Django Endpoints

### Payment Result Handlers
- **Success**: `/payments/success/` - Handles successful payment completion
- **Failure**: `/payments/fail/` - Handles failed payment attempts
- **Cancel**: `/payments/cancel/` - Handles user-cancelled payments

### SumUp-Specific Endpoints
- **Webhook**: `/payments/sumup/webhook/` - Receives payment status updates from SumUp
- **OAuth Callback**: `/payments/sumup/oauth/callback/` - Handles OAuth authorization callback
- **OAuth Connect**: `/payments/sumup/oauth/connect/<artist_id>/` - Initiates OAuth flow for artists

### Checkout Flow
- **Main Checkout**: `/payments/checkout/` - Primary checkout page
- **Payment Method Selection**: `/payments/select-method/` - Choose payment provider
- **SumUp Checkout**: `/payments/sumup/checkout/<order_id>/` - SumUp-specific checkout
- **Connected Checkout**: `/payments/sumup/connected-checkout/<order_id>/` - For connected accounts
- **Checkout Widget**: `/payments/checkout-widget/<checkout_id>/` - Embedded checkout widget

## Views Implementation

### Payment Result Views
- `PaymentSuccessView` - Class-based view for success page
- `PaymentFailedView` - Class-based view for failure page
- `PaymentCancelView` - Class-based view for cancellation page
- `payment_success()` - Function-based handler for success
- `payment_fail()` - Function-based handler for failure
- `payment_cancel()` - Function-based handler for cancellation

### SumUp Integration Views
- `SumUpCallbackView` - Handles payment callbacks from SumUp
- `SumUpWebhookView` - Processes webhook notifications
- `sumup_connect_start()` - Initiates OAuth connection
- `sumup_connect_callback()` - Completes OAuth authorization
- `sumup_webhook()` - Processes webhook events

## Templates
- `payments/success.html` - Success page template
- `payments/failed.html` - Failure page template
- `payments/cancel.html` - Cancellation page template (newly created)

## Testing

### Endpoint Verification
All endpoints have been tested and are accessible via the ngrok URL:
```bash
python3 test_sumup_endpoints.py
```

### Testing Checklist
- ✅ Environment variables configured with full URLs
- ✅ Django views created for all payment states
- ✅ URL patterns properly configured
- ✅ OAuth callback handler implemented
- ✅ Webhook handler implemented
- ✅ All endpoints accessible via ngrok

## Next Steps

1. **Register Webhook URL with SumUp**:
   - Log into SumUp Dashboard
   - Navigate to Developer Settings
   - Add webhook URL: `https://86a7ab44d9e2.ngrok-free.app/payments/sumup/webhook/`

2. **Configure OAuth Application**:
   - Set redirect URI in SumUp app settings
   - Ensure client credentials match

3. **Test Payment Flow**:
   - Create a test order
   - Complete payment through SumUp
   - Verify webhook receives notification
   - Check order status updates

## Security Notes

- CSRF protection is disabled for webhook endpoint (`@csrf_exempt`)
- Webhook signatures should be verified in production
- OAuth state parameter is used to prevent CSRF attacks
- Session-based order tracking for anonymous users

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Events**:
   - Verify webhook URL is registered in SumUp dashboard
   - Check ngrok tunnel is running
   - Review Django logs for errors

2. **OAuth Callback Fails**:
   - Ensure redirect URI matches exactly in SumUp settings
   - Check state parameter is maintained across requests
   - Verify session middleware is enabled

3. **Payment Status Not Updating**:
   - Check webhook handler logic
   - Verify order lookup by checkout ID
   - Review transaction status mapping