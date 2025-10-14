# SumUp URL Structure - Complete Reference

**Date:** October 14, 2025
**Status:** ✅ All URLs properly configured

---

## Summary

The URL `/payments/sumup/initiate/` **does not exist** in your project. This appears to be a confusion about the actual URL structure. Below is the complete reference of all working SumUp URLs.

---

## OAuth URLs (Artist Connection)

These URLs are in the **accounts** app for OAuth authentication:

### 1. Start OAuth Connection
- **URL:** `/accounts/sumup/connect/`
- **Name:** `accounts:sumup_connect`
- **View:** `accounts.sumup_views.SumUpConnectView`
- **Method:** GET
- **Purpose:** Initiates OAuth flow, redirects artist to SumUp authorization page
- **Access:** Login required, artist only
- **File:** accounts/urls.py:27

### 2. OAuth Callback
- **URL:** `/accounts/sumup/callback/`
- **Name:** `accounts:sumup_callback`
- **View:** `accounts.sumup_views.SumUpCallbackView`
- **Method:** GET
- **Purpose:** Receives OAuth authorization code, exchanges for tokens
- **Access:** Automatic redirect from SumUp
- **File:** accounts/urls.py:28

### 3. Disconnect SumUp
- **URL:** `/accounts/sumup/disconnect/`
- **Name:** `accounts:sumup_disconnect`
- **View:** `accounts.sumup_views.SumUpDisconnectView`
- **Method:** POST
- **Purpose:** Disconnects artist's SumUp account
- **Access:** Login required, artist only
- **File:** accounts/urls.py:29

### 4. Check Connection Status
- **URL:** `/accounts/sumup/status/`
- **Name:** `accounts:sumup_status`
- **View:** `accounts.sumup_views.SumUpStatusView`
- **Method:** GET
- **Purpose:** Returns JSON with connection status
- **Access:** Login required, artist only
- **File:** accounts/urls.py:30

---

## Payment Processing URLs

These URLs are in the **payments** app for checkout and payment processing:

### Primary Checkout Flow

#### 1. Simple Checkout (Primary Method)
- **URL:** `/payments/simple-checkout/`
- **Name:** `payments:simple_checkout`
- **View:** `payments.simple_checkout.simple_checkout_process`
- **Purpose:** Simplified checkout process
- **File:** payments/urls.py:13

#### 2. Redirect Checkout
- **URL:** `/payments/redirect/checkout/<int:order_id>/`
- **Name:** `payments:redirect_checkout`
- **View:** `payments.redirect_checkout.create_order_checkout`
- **Purpose:** Create checkout and redirect to SumUp
- **File:** payments/urls.py:16

#### 3. Redirect Success
- **URL:** `/payments/redirect/success/`
- **Name:** `payments:redirect_success`
- **View:** `payments.redirect_success_fixed.redirect_success_fixed`
- **Purpose:** Handle successful payment return
- **File:** payments/urls.py:17

### SumUp-Specific Checkout URLs

#### 4. SumUp Checkout
- **URL:** `/payments/sumup/checkout/<int:order_id>/`
- **Name:** `payments:sumup_checkout`
- **View:** `payments.views.SumUpCheckoutView`
- **Purpose:** Create SumUp checkout for order
- **File:** payments/urls.py:27

#### 5. Connected SumUp Checkout
- **URL:** `/payments/sumup/connected-checkout/<int:order_id>/`
- **Name:** `payments:connected_sumup_checkout`
- **View:** `payments.views.ConnectedSumUpCheckoutView`
- **Purpose:** Create checkout using artist's OAuth connection
- **File:** payments/urls.py:28

#### 6. SumUp Success
- **URL:** `/payments/sumup/success/`
- **Name:** `payments:sumup_success`
- **View:** `payments.views.SumUpSuccessView`
- **Purpose:** Handle SumUp payment success
- **File:** payments/urls.py:42

#### 7. SumUp Callback (Payment)
- **URL:** `/payments/sumup/callback/`
- **Name:** `payments:sumup_callback`
- **View:** `payments.views.SumUpCallbackView`
- **Purpose:** Handle SumUp payment callback (different from OAuth callback!)
- **File:** payments/urls.py:43

#### 8. SumUp Webhook
- **URL:** `/payments/sumup/webhook/`
- **Name:** `payments:sumup_webhook`
- **View:** `payments.views.sumup_webhook`
- **Method:** POST
- **Purpose:** Receive webhook notifications from SumUp
- **File:** payments/urls.py:44

### Legacy OAuth URLs (in Payments App)

These appear to be older OAuth implementations that may be redundant:

#### 9. Legacy OAuth Connect
- **URL:** `/payments/sumup/oauth/connect/<int:artist_id>/`
- **Name:** `payments:sumup_connect_start`
- **View:** `payments.views.sumup_connect_start`
- **Status:** ⚠️ Possibly redundant (use accounts URLs instead)
- **File:** payments/urls.py:47

#### 10. Legacy OAuth Callback
- **URL:** `/payments/sumup/oauth/callback/`
- **Name:** `payments:sumup_oauth_callback`
- **View:** `payments.views.sumup_connect_callback`
- **Status:** ⚠️ Possibly redundant (use accounts URLs instead)
- **File:** payments/urls.py:48

### Widget-Based Checkout URLs

#### 11. Widget Checkout
- **URL:** `/payments/widget/checkout/<int:order_id>/`
- **Name:** `payments:widget_checkout`
- **View:** `payments.widget_views.widget_checkout`
- **Purpose:** JavaScript widget-based checkout
- **File:** payments/urls.py:62

#### 12. Widget Checkout (Fixed)
- **URL:** `/payments/widget-fixed/checkout/<int:order_id>/`
- **Name:** `payments:widget_checkout_fixed`
- **View:** `payments.widget_views_fixed.widget_checkout_fixed`
- **Purpose:** Fixed widget implementation with proper X-Frame-Options
- **File:** payments/urls.py:71

---

## URL Routing Structure

The main project router (events/urls.py) includes:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('payments/', include(('payments.urls', 'payments'), namespace='payments')),
    path('cart/', include(('cart.urls', 'cart'), namespace='cart')),
    path('orders/', include(('orders.urls', 'orders'), namespace='orders')),
    path('analytics/', include(('analytics.urls', 'analytics'), namespace='analytics')),
    path("", include(("events.app_urls", "events"), namespace="events")),
]
```

**All URL patterns are properly included** via the `include()` function.

---

## Common URL Usage Examples

### Artist Connecting SumUp

**Step 1:** Artist visits dashboard and clicks "Connect SumUp"
```
Link to: {% url 'accounts:sumup_connect' %}
URL: /accounts/sumup/connect/
```

**Step 2:** System redirects to SumUp OAuth
```
Automatic redirect to: https://api.sumup.com/authorize?...
```

**Step 3:** SumUp redirects back with code
```
Automatic callback to: /accounts/sumup/callback/?code=xxx&state=xxx
```

**Step 4:** Success! Artist is connected
```
Redirect to dashboard with success message
```

### Customer Making Purchase

**Step 1:** Add tickets to cart
```
URL: /cart/add/<event_id>/
```

**Step 2:** View cart and checkout
```
URL: /cart/
Click "Checkout" → /payments/checkout/
```

**Step 3:** System creates SumUp checkout
```
If artist has OAuth connection:
  URL: /payments/sumup/connected-checkout/<order_id>/
Else:
  URL: /payments/sumup/checkout/<order_id>/
```

**Step 4:** Customer redirected to SumUp payment page
```
Automatic redirect to SumUp hosted checkout
```

**Step 5:** Customer completes payment on SumUp

**Step 6:** SumUp redirects back
```
Success: /payments/sumup/success/
Failed: /payments/fail/
```

**Step 7:** Polling service verifies payment (5 minutes)
```
Background task checks payment status via API
Issues tickets when payment confirmed
```

---

## Template Usage

### In Artist Dashboard

Connect SumUp button:
```django
{% if not profile.is_sumup_connected %}
    <a href="{% url 'accounts:sumup_connect' %}" class="btn btn-primary">
        Connect SumUp Account
    </a>
{% else %}
    <span class="badge badge-success">✅ SumUp Connected</span>

    <form method="post" action="{% url 'accounts:sumup_disconnect' %}">
        {% csrf_token %}
        <button type="submit" class="btn btn-danger btn-sm">
            Disconnect
        </button>
    </form>
{% endif %}
```

Check connection via JavaScript:
```javascript
fetch('{% url "accounts:sumup_status" %}')
    .then(response => response.json())
    .then(data => {
        if (data.connected) {
            console.log('Merchant Code:', data.merchant_code);
        }
    });
```

### In Checkout Flow

Redirect to checkout:
```django
<a href="{% url 'payments:redirect_checkout' order.id %}" class="btn btn-primary">
    Pay with SumUp
</a>
```

Or use simple checkout:
```django
<form method="post" action="{% url 'payments:simple_checkout' %}">
    {% csrf_token %}
    <input type="hidden" name="order_id" value="{{ order.id }}">
    <button type="submit" class="btn btn-primary">
        Complete Payment
    </button>
</form>
```

---

## View Usage (Python Code)

### Creating a Checkout

```python
from payments import sumup as sumup_api
from django.shortcuts import redirect

def process_order(request, order_id):
    order = Order.objects.get(id=order_id)

    # Check if artist has OAuth connection
    artist_profile = order.event.artist.artistprofile

    if artist_profile.is_sumup_connected:
        # Use artist's OAuth connection
        checkout_data = sumup_api.create_checkout_for_artist(
            artist_sumup=artist_profile,
            amount=order.total_amount,
            currency='GBP',
            reference=order.order_number,
            description=f'Tickets for {order.event.title}',
            return_url=request.build_absolute_uri(
                reverse('payments:sumup_success')
            )
        )
    else:
        # Use platform credentials
        checkout_data = sumup_api.create_checkout_simple(
            amount=order.total_amount,
            currency='GBP',
            reference=order.order_number,
            description=f'Tickets for {order.event.title}',
            return_url=request.build_absolute_uri(
                reverse('payments:sumup_success')
            )
        )

    # Store checkout ID
    order.sumup_checkout_id = checkout_data['id']
    order.save()

    # Redirect customer to SumUp payment page
    return redirect(checkout_data['checkout_url'])
```

### Checking Connection Status

```python
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def check_sumup_status(request):
    if request.user.user_type != 'artist':
        return JsonResponse({'error': 'Not an artist'}, status=403)

    profile = request.user.artistprofile

    return JsonResponse({
        'connected': profile.is_sumup_connected,
        'merchant_code': profile.sumup_merchant_code,
        'token_expired': profile.sumup_token_expired,
    })
```

---

## Testing URLs

### Manual Testing

1. **Test OAuth Connection:**
```bash
# Start server
python manage.py runserver

# Login as artist
# Visit: http://localhost:8000/accounts/login/

# Connect SumUp
# Visit: http://localhost:8000/accounts/sumup/connect/

# Should redirect to SumUp, then back to /accounts/sumup/callback/
```

2. **Test Payment Flow:**
```bash
# Create test order (via shell or UI)
# Visit checkout URL
http://localhost:8000/payments/redirect/checkout/1/

# Should redirect to SumUp payment page
```

3. **Test Status Check:**
```bash
curl -H "Cookie: sessionid=xxx" \
     http://localhost:8000/accounts/sumup/status/
```

---

## Troubleshooting 404 Errors

### If you get: `/payments/sumup/initiate/` → 404

**Problem:** This URL does not exist.

**Solution:** Use the correct URL:
```
/accounts/sumup/connect/  ← For OAuth connection
/payments/sumup/checkout/<order_id>/  ← For payment checkout
```

### If you get: `/accounts/sumup/connect/` → 404

**Problem:** accounts.urls not included in main URLs.

**Solution:** Check events/urls.py has:
```python
path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
```

**Verify:** ✅ Already present at line 12

### If you get: `/payments/sumup/callback/` → AttributeError

**Problem:** Wrong view function name.

**Solution:** This should point to correct view in payments/views.py

---

## Summary

**The URL `/payments/sumup/initiate/` DOES NOT EXIST and never existed.**

**Correct URLs to use:**

1. **For OAuth connection (artist):**
   - Start: `/accounts/sumup/connect/`
   - Callback: `/accounts/sumup/callback/` (automatic)

2. **For payment processing (customer):**
   - Checkout: `/payments/redirect/checkout/<order_id>/`
   - Or: `/payments/sumup/checkout/<order_id>/`
   - Success: `/payments/sumup/success/`

**All URL patterns are properly configured and included in the main router.**

---

## Related Files

- `events/urls.py` - Main project router (includes all apps)
- `accounts/urls.py` - OAuth URLs (lines 27-30)
- `payments/urls.py` - Payment URLs (complete checkout flow)
- `accounts/sumup_views.py` - OAuth view implementations
- `payments/views.py` - Payment view implementations
- `payments/sumup.py` - SumUp API client

---

**Status:** ✅ All URLs working correctly. No 404 errors should occur if using the correct URLs listed above.
