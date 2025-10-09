#!/usr/bin/env python
"""Test SumUp script loading and widget initialization."""

import os
import sys
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'events.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
from payments.widget_service import SumUpWidgetService
from payments import sumup as sumup_api
from orders.models import Order, OrderItem
from events.models import Event
from accounts.models import User, ArtistProfile
import uuid

def test_script_loading_verification():
    """Create a test page to verify script loading."""
    print("\n" + "="*60)
    print("TESTING SUMUP SCRIPT LOADING")
    print("="*60)

    # Create a real checkout for testing
    try:
        checkout_ref = f"script_test_{uuid.uuid4().hex[:8]}"
        checkout_data = sumup_api.create_checkout_simple(
            amount=25.00,
            currency="GBP",
            reference=checkout_ref,
            description="Script loading test",
            return_url=f"{settings.SITE_URL}/test/success/",
            redirect_url=f"{settings.SITE_URL}/test/success/"
        )

        checkout_id = checkout_data.get('id')
        print(f"✅ Test checkout created: {checkout_id}")

        # Generate test HTML with improved script loading
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SumUp Script Loading Test</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">

    <!-- SumUp Widget SDK with improved loading -->
    <script>
    // Debug logging
    function debugLog(message, type = 'info') {{
        const timestamp = new Date().toLocaleTimeString();
        const color = type === 'error' ? 'red' : type === 'success' ? 'green' : 'blue';
        console.log(`%c[$${{timestamp}}] $${{message}}`, `color: $${{color}}`);

        // Also show in page if debug element exists
        const debugElement = document.getElementById('debug-output');
        if (debugElement) {{
            debugElement.innerHTML += `<div style="color: $${{color}}">[$${{timestamp}}] $${{message}}</div>`;
            debugElement.scrollTop = debugElement.scrollHeight;
        }}
    }}

    // Function to load SumUp SDK with detailed logging
    function loadSumUpSDK() {{
        return new Promise((resolve, reject) => {{
            debugLog('Starting SumUp SDK load...', 'info');

            const script = document.createElement('script');
            script.src = 'https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js';
            script.async = true;

            script.onload = () => {{
                debugLog('SDK script loaded successfully', 'success');

                // Check if SumUpCard is available
                if (typeof SumUpCard !== 'undefined') {{
                    debugLog('SumUpCard object is available!', 'success');
                    debugLog(`SumUpCard type: ${{typeof SumUpCard}}`, 'info');
                    debugLog(`SumUpCard.mount type: ${{typeof SumUpCard.mount}}`, 'info');
                    resolve();
                }} else {{
                    debugLog('SumUpCard object not found after SDK load', 'error');
                    reject(new Error('SumUpCard not available'));
                }}
            }};

            script.onerror = (error) => {{
                debugLog(`Failed to load SumUp SDK: ${{error}}`, 'error');
                reject(new Error('Failed to load SumUp SDK'));
            }};

            debugLog(`Appending script tag with src: ${{script.src}}`, 'info');
            document.head.appendChild(script);
        }});
    }}
    </script>

    <!-- Alternative: Direct script loading -->
    <script src="https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js" async></script>

    <style>
        #sumup-widget {{
            min-height: 400px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        #debug-output {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            max-height: 300px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.85em;
        }}
    </style>
</head>
<body>
    <div class="container mt-5">
        <h1 class="mb-4">SumUp Script Loading Test</h1>

        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Widget Container</h5>
                    </div>
                    <div class="card-body">
                        <div id="sumup-widget">
                            <div class="text-center" id="loading-indicator">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2">Loading SumUp widget...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h6>Test Configuration</h6>
                    </div>
                    <div class="card-body">
                        <p><strong>Checkout ID:</strong><br>{checkout_id}</p>
                        <p><strong>Amount:</strong> £25.00</p>
                        <p><strong>Currency:</strong> GBP</p>
                        <p><strong>SDK URL:</strong><br>https://gateway.sumup.com/gateway/ecom/card/v2/sdk.js</p>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h6>Debug Output</h6>
                    </div>
                    <div class="card-body">
                        <div id="debug-output"></div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h6>Test Actions</h6>
                    </div>
                    <div class="card-body">
                        <button class="btn btn-primary btn-sm mb-2 w-100" onclick="testSDKAvailability()">
                            Test SDK Availability
                        </button>
                        <button class="btn btn-success btn-sm mb-2 w-100" onclick="initializeWidget()">
                            Initialize Widget
                        </button>
                        <button class="btn btn-warning btn-sm w-100" onclick="clearDebug()">
                            Clear Debug Log
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Test functions
        function testSDKAvailability() {{
            debugLog('=== SDK Availability Test ===', 'info');
            debugLog(`SumUpCard available: ${{typeof SumUpCard !== 'undefined'}}`, 'info');

            if (typeof SumUpCard !== 'undefined') {{
                debugLog(`SumUpCard type: ${{typeof SumUpCard}}`, 'success');
                debugLog(`SumUpCard.mount available: ${{typeof SumUpCard.mount === 'function'}}`, 'success');

                // Test if we can call mount (without actually mounting)
                try {{
                    // This should throw an error for missing parameters, but shouldn't crash
                    debugLog('Testing SumUpCard.mount function call...', 'info');
                    // SumUpCard.mount({{}}); // Commented out to avoid errors
                    debugLog('SumUpCard.mount function exists and is callable', 'success');
                }} catch (error) {{
                    debugLog(`SumUpCard.mount test error (expected): ${{error.message}}`, 'info');
                }}
            }} else {{
                debugLog('SumUpCard not available - SDK may not be loaded', 'error');
            }}
        }}

        function initializeWidget() {{
            debugLog('=== Widget Initialization Test ===', 'info');

            if (typeof SumUpCard === 'undefined') {{
                debugLog('SumUpCard not available, attempting to load SDK...', 'error');
                loadSumUpSDK().then(() => {{
                    debugLog('SDK loaded successfully, retrying widget init...', 'success');
                    mountWidget();
                }}).catch(error => {{
                    debugLog(`SDK loading failed: ${{error.message}}`, 'error');
                }});
                return;
            }}

            mountWidget();
        }}

        function mountWidget() {{
            try {{
                debugLog('Mounting SumUp widget...', 'info');

                SumUpCard.mount({{
                    id: 'sumup-widget',
                    checkoutId: '{checkout_id}',
                    showSubmitButton: true,
                    showFooter: true,
                    amount: 25.00,
                    currency: 'GBP',
                    locale: 'en-GB',
                    onResponse: function (type, body) {{
                        debugLog(`Widget response: ${{type}}`, 'info');
                        debugLog(`Response body: ${{JSON.stringify(body)}}`, 'info');
                    }},
                    onLoad: function() {{
                        debugLog('Widget loaded successfully!', 'success');
                        document.getElementById('loading-indicator').style.display = 'none';
                    }},
                    onError: function(error) {{
                        debugLog(`Widget error: ${{error.message || error}}`, 'error');
                    }}
                }});

                debugLog('SumUpCard.mount() called successfully', 'success');

            }} catch (error) {{
                debugLog(`Error mounting widget: ${{error.message}}`, 'error');
                debugLog(`Error stack: ${{error.stack}}`, 'error');
            }}
        }}

        function clearDebug() {{
            document.getElementById('debug-output').innerHTML = '';
        }}

        // Auto-initialize
        document.addEventListener('DOMContentLoaded', function() {{
            debugLog('🚀 Page loaded - SumUp script loading test starting', 'success');

            // Test SDK availability immediately
            setTimeout(() => {{
                testSDKAvailability();
            }}, 1000);

            // Auto-initialize widget after 3 seconds
            setTimeout(() => {{
                debugLog('Auto-initializing widget...', 'info');
                initializeWidget();
            }}, 3000);
        }});

        // Capture global errors
        window.addEventListener('error', function(event) {{
            debugLog(`💥 Global error: ${{event.message}}`, 'error');
            debugLog(`File: ${{event.filename}}:${{event.lineno}}`, 'error');
        }});
    </script>
</body>
</html>
"""

        # Save the test file
        with open('/Users/josegalan/Documents/jersey_music/test_script_loading.html', 'w') as f:
            f.write(html_content)

        print(f"✅ Test page created: test_script_loading.html")
        print(f"✅ Checkout ID: {checkout_id}")
        print(f"✅ Amount: £25.00")

        return True

    except Exception as e:
        print(f"❌ Failed to create test: {e}")
        return False

def main():
    print("="*60)
    print("SUMUP SCRIPT LOADING VERIFICATION")
    print("="*60)

    success = test_script_loading_verification()

    if success:
        print("\n📋 Test Instructions:")
        print("1. Open test_script_loading.html in a browser")
        print("2. Open browser Developer Tools (F12)")
        print("3. Check Console tab for detailed logs")
        print("4. Check Network tab for script loading")
        print("5. Watch the debug output on the page")
        print("6. Look for these success indicators:")
        print("   - 'SumUpCard object is available!'")
        print("   - 'Widget loaded successfully!'")
        print("   - No red error messages")

    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

if __name__ == '__main__':
    main()