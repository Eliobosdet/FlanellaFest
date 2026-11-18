# Flanella Fest Website

Official website repository for Flanella Fest.

Official website: www.flanellafest.it
Instagram: https://www.instagram.com/flanellafest/

## Technology Stack

* Python 3.12

* Django 4.2

* SQLite / PostgreSQL

* Stripe API

* Bootstrap / HTML5

## Prerequisites

* Python 3.12 or higher

* Pipenv or venv

## Local Setup and Running

1. Clone the repository:

   ```
   git clone https://github.com/eliobosdet/flanellafest.git
   cd FlanellaFest-main
   
   ```

2. Set up the virtual environment and install dependencies:

   ```
   pipenv shell
   pip install -r requirements.txt
   
   ```

3. Create a `.env` file in the project root with the following environment variables:

   ```
   SECRET_KEY=your_secret_key
   DEBUG=True
   STRIPE_SECRET_KEY=your_stripe_secret_key
   STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
   
   ```

4. Run database migrations:

   ```
   python manage.py migrate
   
   ```

5. Start the development server:

   ```
   python manage.py runserver
   
   ```

## Running Tests

To run the automated test suite:

```
python manage.py test festival

```