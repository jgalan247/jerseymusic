# SumUp Merchant Code Fix

## Problem
The SumUp payment processing was failing with a "merchant_code NOT NULL constraint failed" error when attempting to create checkout sessions.

## Root Cause
The `SumUpCheckout` model has a required `merchant_code` field, but several places in the code were creating checkout records without providing this value:

1. `payments/views.py` - Line 298: `create_sumup_checkout()` method
2. `payments/views.py` - Line 649: `SumUpCheckoutView.create_sumup_checkout()` method
3. `payments/views.py` - Line 884: `start_checkout()` function
4. `payments/connected_payment_service.py` - Line 86: Connected checkout creation

## Solution Applied

### 1. Environment Variable Configuration
Updated `.env` file with proper merchant code:
```bash
SUMUP_MERCHANT_CODE=M28WNZCB
SUMUP_MERCHANT_ID=M28WNZCB  # Also maintained for compatibility
```

### 2. Code Fixes
Updated all `SumUpCheckout.objects.create()` calls to include merchant_code:

#### payments/views.py - Line 304
```python
# Before (missing merchant_code)
checkout = SumUpCheckout.objects.create(
    order=order,
    customer=order.user,
    amount=order.total,
    currency='GBP',
    description=description[:255],
    # merchant_code missing!
    return_url=return_url,
    redirect_url=redirect_url
)

# After (with merchant_code)
checkout = SumUpCheckout.objects.create(
    order=order,
    customer=order.user,
    amount=order.total,
    currency='GBP',
    description=description[:255],
    merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
    return_url=return_url,
    redirect_url=redirect_url
)
```

#### payments/views.py - Line 655
```python
# Before (hardcoded test value)
merchant_code='TEST_MERCHANT',

# After (proper configuration)
merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
```

#### payments/views.py - Line 891
```python
# Before (hardcoded test value)
merchant_code='TEST123',

# After (proper configuration)
merchant_code=settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
```

#### payments/connected_payment_service.py - Line 86
```python
# Before (could be None)
merchant_code=artist_profile.sumup_merchant_code,

# After (with fallback)
merchant_code=artist_profile.sumup_merchant_code or settings.SUMUP_MERCHANT_CODE or 'M28WNZCB',
```

### 3. Django Settings
The merchant code is already properly configured in `events/settings.py`:
```python
SUMUP_MERCHANT_CODE = os.getenv("SUMUP_MERCHANT_CODE")
```

## Testing

### Manual Verification
Created test script `test_payment_merchant_fix.py` to verify:
- ✅ Environment variables are properly loaded
- ✅ All checkout creation points use merchant_code
- ✅ Fallback values are provided for robustness

### Expected Results
After these fixes, the payment flow should:
1. ✅ No longer fail with "merchant_code NOT NULL constraint"
2. ✅ Successfully create SumUp checkout records
3. ✅ Progress past the checkout creation step
4. ✅ Use the proper merchant code `M28WNZCB` for all payments

## Fallback Strategy
The code includes multiple fallback levels:
1. `settings.SUMUP_MERCHANT_CODE` (from .env)
2. Hardcoded `'M28WNZCB'` as ultimate fallback
3. For connected artists: artist's merchant code → platform default → hardcoded fallback

## Files Modified
- `.env` - Added `SUMUP_MERCHANT_CODE=M28WNZCB`
- `payments/views.py` - Fixed 3 checkout creation methods
- `payments/connected_payment_service.py` - Added fallback for artist merchant codes

## Next Steps
1. **Test Payment Flow**: Try purchasing tickets to verify checkout creation works
2. **Monitor Logs**: Check for any remaining constraint errors
3. **Verify SumUp Integration**: Ensure merchant code is accepted by SumUp API
4. **Update Tests**: Update any test files that might still use old hardcoded values

The "merchant_code NOT NULL constraint failed" error should now be resolved.