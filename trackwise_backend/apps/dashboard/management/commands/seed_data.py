"""
python manage.py seed_data

Creates a demo user with realistic Indian professional data:
- 30 days of expenses across 7 categories
- 15 learning sessions with varied sources
- 5 goals at different stages
- 8 savings entries across investment types

Demo login: demo@trackwise.in / Demo1234!
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from trackwise_backend.apps.accounts.models import Profile
from trackwise_backend.apps.expenses.models import Expense
from trackwise_backend.apps.learning.models import LearningSession
from trackwise_backend.apps.goals.models import Goal
from trackwise_backend.apps.savings.models import SavingEntry
from trackwise_backend.apps.subscriptions.models import Subscription

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed database with realistic demo data for TrackWise'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing demo user data first')

    def handle(self, *args, **options):
        email = 'demo@trackwise.in'
        password = 'Demo1234!'

        if options['reset']:
            User.objects.filter(email=email).delete()
            self.stdout.write('Deleted existing demo user')

        # Create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'full_name': 'Arjun Mehta', 'is_email_verified': True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user: {email}'))
        else:
            self.stdout.write(f'User exists: {email}')

        # Profile
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={'monthly_income': 85000, 'currency': 'INR', 'timezone': 'Asia/Kolkata'},
        )

        # Subscription (trial)
        Subscription.objects.get_or_create(
            user=user,
            defaults={
                'status': 'trial',
                'trial_ends_at': timezone.now() + timedelta(days=5),
            },
        )

        today = date.today()

        # ── EXPENSES (30 days) ────────────────────────────────
        if not Expense.objects.filter(user=user).exists():
            expenses = []
            food_items = [
                ('Zomato dinner', 380), ('Swiggy lunch', 250), ('Groceries DMart', 1200),
                ('Coffee Blue Tokai', 180), ('Chai tapri', 30), ('Kirana store', 450),
                ('Blinkit groceries', 650), ('Dominos pizza', 520), ('Thali lunch', 120),
                ('Fruits vendor', 200), ('Milk monthly', 900), ('Restaurant dinner', 1400),
            ]
            transport_items = [
                ('Uber office', 180), ('Ola airport', 650), ('Metro recharge', 500),
                ('Rapido bike', 80), ('Petrol', 1500), ('Auto rickshaw', 50),
            ]
            entertainment_items = [
                ('Netflix subscription', 649), ('Spotify premium', 119),
                ('Hotstar annual', 299), ('Movie tickets PVR', 700),
                ('Zee5 monthly', 99), ('Book - Atomic Habits', 350),
            ]
            shopping_items = [
                ('Amazon electronics', 2500), ('Myntra clothes', 1800),
                ('Flipkart headphones', 1200), ('Decathlon sports', 900),
            ]
            bills_items = [
                ('Electricity bill', 1800), ('WiFi Airtel', 799),
                ('Mobile recharge', 599), ('Water bill', 200),
                ('Gas cylinder', 900), ('Society maintenance', 3500),
            ]
            learning_items = [
                ('Udemy course', 449), ('Coursera subscription', 3000),
                ('O\'Reilly books', 500),
            ]

            for day_offset in range(30):
                d = today - timedelta(days=day_offset)

                # 1-3 food items per day
                for _ in range(random.randint(1, 3)):
                    item = random.choice(food_items)
                    variation = random.uniform(0.8, 1.3)
                    expenses.append(Expense(
                        user=user, date=d, description=item[0],
                        category='Food', amount=round(item[1] * variation),
                        payment=random.choice(['UPI', 'Cash', 'Card']),
                    ))

                # Transport every other day
                if day_offset % 2 == 0:
                    item = random.choice(transport_items)
                    expenses.append(Expense(
                        user=user, date=d, description=item[0],
                        category='Transport', amount=item[1],
                        payment='UPI',
                    ))

                # Entertainment weekly
                if day_offset % 7 == 0:
                    item = random.choice(entertainment_items)
                    expenses.append(Expense(
                        user=user, date=d, description=item[0],
                        category='Entertainment', amount=item[1],
                        payment='Card',
                    ))

                # Shopping bi-weekly
                if day_offset % 14 == 0:
                    item = random.choice(shopping_items)
                    expenses.append(Expense(
                        user=user, date=d, description=item[0],
                        category='Shopping', amount=item[1],
                        payment='Card',
                    ))

                # Bills monthly (first week)
                if day_offset < 7 and day_offset < len(bills_items):
                    item = bills_items[day_offset]
                    expenses.append(Expense(
                        user=user, date=d, description=item[0],
                        category='Bills', amount=item[1],
                        payment='Netbanking',
                    ))

            # Learning expenses
            for item in learning_items:
                expenses.append(Expense(
                    user=user, date=today - timedelta(days=random.randint(1, 25)),
                    description=item[0], category='Learning',
                    amount=item[1], payment='Card',
                ))

            Expense.objects.bulk_create(expenses)
            self.stdout.write(self.style.SUCCESS(f'  {len(expenses)} expenses created'))

        # ── LEARNING SESSIONS ─────────────────────────────────
        if not LearningSession.objects.filter(user=user).exists():
            sessions = [
                ('System Design fundamentals', 'YouTube', 2.5, 'In Progress', 1),
                ('React Native navigation', 'Online Course', 1.5, 'Completed', 2),
                ('Docker & Kubernetes', 'Documentation', 1.0, 'In Progress', 3),
                ('TypeScript generics', 'Online Course', 2.0, 'Completed', 4),
                ('PostgreSQL optimization', 'Book', 1.5, 'In Progress', 5),
                ('AWS Lambda functions', 'YouTube', 2.0, 'Completed', 6),
                ('GraphQL API design', 'Online Course', 1.0, 'On Hold', 8),
                ('Redis caching patterns', 'Documentation', 0.5, 'Completed', 9),
                ('Next.js 14 features', 'YouTube', 3.0, 'Completed', 10),
                ('Flutter state management', 'Online Course', 2.0, 'In Progress', 12),
                ('Python async/await', 'Book', 1.5, 'Completed', 14),
                ('CI/CD with GitHub Actions', 'Documentation', 1.0, 'Completed', 16),
                ('Tailwind CSS advanced', 'YouTube', 1.0, 'Completed', 18),
                ('LLM prompt engineering', 'Podcast', 0.5, 'In Progress', 20),
                ('DynamoDB data modeling', 'Online Course', 2.0, 'On Hold', 25),
            ]
            objs = [
                LearningSession(
                    user=user, date=today - timedelta(days=d),
                    topic=topic, source=source, hours=hrs, status=status,
                )
                for topic, source, hrs, status, d in sessions
            ]
            LearningSession.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} learning sessions created'))

        # ── GOALS ──────────────────────────────────────────────
        if not Goal.objects.filter(user=user).exists():
            goals = [
                ('Emergency Fund', 'Finance', 300000, 75000, 180),
                ('Learn System Design', 'Learning', 100, 42, 90),
                ('Side Project Launch', 'Career', 50, 38, 45),
                ('Save for Europe Trip', 'Travel', 200000, 180000, 120),
                ('Read 24 Books', 'Personal', 24, 9, 270),
            ]
            objs = [
                Goal(
                    user=user, name=name, category=cat,
                    target=target, current=current,
                    deadline=today + timedelta(days=days),
                )
                for name, cat, target, current, days in goals
            ]
            Goal.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} goals created'))

        # ── SAVINGS ────────────────────────────────────────────
        if not SavingEntry.objects.filter(user=user).exists():
            savings = [
                ('Nifty 50 Index SIP', 'SIP', 5000, 'Zerodha'),
                ('HDFC FD 7.2%', 'FD', 10000, 'HDFC Bank'),
                ('PPF Annual', 'PPF', 12500, 'SBI'),
                ('Sovereign Gold Bond', 'Gold', 3000, 'RBI'),
                ('Axis Bluechip MF', 'SIP', 3000, 'Groww'),
                ('NPS Tier 1', 'NPS', 5000, 'HDFC Pension'),
                ('RD Monthly', 'RD', 2000, 'ICICI Bank'),
                ('Savings Account', 'Savings Account', 5000, 'Kotak'),
            ]
            objs = [
                SavingEntry(
                    user=user, date=today - timedelta(days=i * 3),
                    name=name, inv_type=typ, amount=amt,
                    monthly_income=85000, platform=platform,
                )
                for i, (name, typ, amt, platform) in enumerate(savings)
            ]
            SavingEntry.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} savings entries created'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Seed data complete!'))
        self.stdout.write(f'   Login: {email} / {password}')
        self.stdout.write(f'   Expenses: {Expense.objects.filter(user=user).count()}')
        self.stdout.write(f'   Learning: {LearningSession.objects.filter(user=user).count()}')
        self.stdout.write(f'   Goals:    {Goal.objects.filter(user=user).count()}')
        self.stdout.write(f'   Savings:  {SavingEntry.objects.filter(user=user).count()}')
