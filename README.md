# RUN THE WEBSITE ON YOUR PC

## 1. START THE ENVIRONMENT

pipenv shell

## 2. INSTALL THE REQUIREMENTS

pip install -r requirements.txt

## 3. START THE SERVER 

python manage.py runserver

# TEST THE PAYMENTS THROUGH STRIPE

## 1. LOGIN IN YOUR STRIPE DASHBOARD

https://dashboard.stripe.com/

## 2. COPY YOUR SECRET TEST KEYS IN THE .ENV FILE

STRIPE_PUBLIC_KEY='pk_test_...'
STRIPE_SECRET_KEY='sk_test_...'
STRIPE_WEBHOOK_SECRET='whsec_...'

## 3. START THE STRIPE CLI

stripe listen --forward-to localhost:8000/stripe-webhook/



