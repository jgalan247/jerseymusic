from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def plans(request):
    """Display subscription plans for artists"""
    plans = [
        {
            'name': 'Starter',
            'price': '£9.99/month',
            'features': [
                'List up to 10 artworks',
                'Basic analytics',
                'Standard support'
            ]
        },
        {
            'name': 'Professional',
            'price': '£24.99/month',
            'features': [
                'List up to 50 artworks',
                'Advanced analytics',
                'Priority support',
                'Featured artist badge'
            ]
        },
        {
            'name': 'Premium',
            'price': '£49.99/month',
            'features': [
                'Unlimited artworks',
                'Premium analytics',
                'Dedicated support',
                'Homepage features',
                'Marketing tools'
            ]
        }
    ]
    return render(request, 'subscriptions/plans.html', {'plans': plans})

@login_required
def subscribe(request, plan_id):
    """Subscribe to a plan"""
    messages.info(request, 'Subscription feature coming soon!')
    return redirect('accounts:artist_dashboard')

@login_required
def dashboard(request):
    return render(request, 'subscriptions/dashboard.html')
