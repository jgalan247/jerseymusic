# HTTPS Development Setup for SumUp Widget

## Why HTTPS is Required

SumUp payment widgets require HTTPS connections for security. This means localhost:8000 (HTTP) won't work for testing payment widgets.

## SSL Certificate Created

A self-signed SSL certificate has been created in the `ssl/` directory:
- `ssl/localhost.crt` - SSL certificate
- `ssl/localhost.key` - Private key

## Starting HTTPS Development Server

### Option 1: Django Management Command
```bash
python manage.py runserver_https
```

### Option 2: Manual Command
```bash
python manage.py runserver --cert ssl/localhost.crt --key ssl/localhost.key
```

### Option 3: Using stunnel (Alternative)
```bash
# Install stunnel
brew install stunnel  # macOS
sudo apt-get install stunnel4  # Ubuntu

# Create stunnel config and run
```

## Browser Security Warning

When you first visit https://localhost:8000, your browser will show a security warning because the certificate is self-signed.

**To proceed:**
1. Click "Advanced" or "Show details"
2. Click "Proceed to localhost (unsafe)" or "Continue to this site"
3. The warning appears because browsers don't trust self-signed certificates
4. This is normal for development and won't affect SumUp widget functionality

## Testing SumUp Widget

Once HTTPS is working:

1. Visit: https://localhost:8000/payments/widget/test/
2. The SumUp widget should load without X-Frame-Options errors
3. Test payment flow with SumUp test card numbers

## SumUp Test Card Numbers

- **Successful payment:** 4000 0000 0000 0002
- **Declined payment:** 4000 0000 0000 0127
- **Insufficient funds:** 4000 0000 0000 0119

## Production Deployment

For production, use a proper SSL certificate from:
- Let's Encrypt (free)
- Cloudflare (free)
- Commercial certificate provider

## Troubleshooting

### OpenSSL not found
```bash
# macOS
brew install openssl

# Ubuntu/Debian
sudo apt-get install openssl

# Windows
# Download from https://slproweb.com/products/Win32OpenSSL.html
```

### Permission errors
```bash
# Make sure you have write permissions to the project directory
chmod +x create_ssl_cert.py
```

### Browser still shows HTTP
- Clear browser cache
- Check URL starts with `https://`
- Restart browser
