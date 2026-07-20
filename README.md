## 1. MOVE TO THE CORRECT DIRECTORY

cd FlanellaFest-main

## 2. START THE ENVIRONMENT

pipenv shell

## 3. START THE SERVER 

python manage.py runserver

## 4. START THE STRIPE CLI

stripe listen --forward-to localhost:8000/stripe-webhook/