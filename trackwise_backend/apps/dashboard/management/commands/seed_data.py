"""
python manage.py seed_data

Creates a demo user with rich, realistic Indian professional data.
Demo user is pre-verified (email+phone) so OTP is skipped for easy testing.

Demo login: demo@trackwise.in / Demo1234!

Also creates 2 test users to verify 2FA flow:
  test1@trackwise.in / Test1234! (has phone, needs both OTPs)
  test2@trackwise.in / Test1234! (no phone, needs email OTP only)
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
    help = 'Seed database with realistic demo data'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete all demo/test users first')

    def handle(self, *args, **options):
        if options['reset']:
            for e in ['demo@trackwise.in', 'test1@trackwise.in', 'test2@trackwise.in']:
                User.objects.filter(email=e).delete()
            self.stdout.write('Deleted existing test users')

        self._create_demo_user()
        self._create_test_users()
        self.stdout.write(self.style.SUCCESS('\n✅ All seed data created!'))

    def _create_demo_user(self):
        """Main demo user — fully verified, rich data, skip OTP on login."""
        email = 'demo@trackwise.in'
        password = 'Demo1234!'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': 'Arjun Mehta',
                'phone': '9876500001',
                'is_email_verified': True,
                'is_phone_verified': True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user: {email}'))
        else:
            # Ensure verified
            user.is_email_verified = True
            user.is_phone_verified = True
            user.phone = '9876500001'
            user.save(update_fields=['is_email_verified', 'is_phone_verified', 'phone'])
            self.stdout.write(f'Demo user exists: {email} (updated verification)')

        Profile.objects.get_or_create(
            user=user,
            defaults={'monthly_income': 85000, 'currency': 'INR', 'timezone': 'Asia/Kolkata'},
        )

        Subscription.objects.get_or_create(
            user=user,
            defaults={'status': 'trial', 'trial_ends_at': timezone.now() + timedelta(days=5)},
        )

        today = date.today()

        # ── EXPENSES (95+ entries over 30 days) ───────────────
        if not Expense.objects.filter(user=user).exists():
            expenses = []
            food = [
                ('Zomato - Biryani Paradise', 380), ('Swiggy - South Indian lunch', 250),
                ('DMart groceries', 1850), ('Blue Tokai coffee', 180), ('Chai tapri', 30),
                ('Kirana store essentials', 520), ('Blinkit fruits & milk', 650),
                ('Dominos pizza night', 620), ('Office canteen thali', 120),
                ('Fruit vendor weekly', 280), ('Amul milk monthly', 940),
                ('Anniversary dinner Olive', 3200), ('Swiggy Instamart snacks', 340),
                ('Haldiram sweets (Diwali)', 800), ('Weekend brunch Social', 1600),
            ]
            transport = [
                ('Uber to office', 180), ('Ola airport pickup', 650), ('Delhi Metro recharge', 500),
                ('Rapido bike ride', 80), ('Indian Oil petrol', 2200), ('Auto to market', 60),
                ('Uber Moto', 45), ('Ola Outstation trip', 2800),
            ]
            entertainment = [
                ('Netflix monthly', 649), ('Spotify premium', 119), ('Hotstar annual', 299),
                ('PVR movie - Pushpa 2', 700), ('Zee5 monthly', 99),
                ('BookMyShow comedy show', 1200), ('PS5 game purchase', 3499),
            ]
            shopping = [
                ('Amazon - USB-C hub', 1800), ('Myntra - winter jacket', 2200),
                ('Flipkart - TWS earbuds', 1500), ('Decathlon running shoes', 2999),
                ('Croma laptop stand', 1200), ('Lenskart frames', 1800),
            ]
            bills = [
                ('TATA Power electricity', 2100), ('Airtel Fiber WiFi', 799),
                ('Jio recharge', 599), ('Delhi Jal Board water', 200),
                ('Indane gas cylinder', 920), ('Society maintenance', 4500),
                ('Health insurance premium', 1500), ('Term insurance', 900),
            ]
            learning_exp = [
                ('Udemy - System Design', 449), ('Coursera Plus annual', 3200),
                ("O'Reilly subscription", 700), ('Kindle books', 299),
            ]
            other = [
                ('Hair cut salon', 300), ('Dry cleaning', 250),
                ('Gym membership', 1500), ('Donation temple', 500),
            ]

            for day_off in range(30):
                d = today - timedelta(days=day_off)

                # 2-4 food items per day
                for _ in range(random.randint(2, 4)):
                    item = random.choice(food)
                    v = random.uniform(0.8, 1.25)
                    expenses.append(Expense(
                        user=user, date=d, description=item[0], category='Food',
                        amount=round(item[1] * v), payment=random.choice(['UPI', 'Cash', 'Card']),
                    ))

                # Transport most days
                if random.random() < 0.7:
                    item = random.choice(transport)
                    expenses.append(Expense(user=user, date=d, description=item[0], category='Transport',
                                            amount=item[1], payment='UPI'))

                # Entertainment weekly
                if day_off % 7 == 0:
                    item = random.choice(entertainment)
                    expenses.append(Expense(user=user, date=d, description=item[0], category='Entertainment',
                                            amount=item[1], payment='Card'))

                # Shopping every 10 days
                if day_off % 10 == 0:
                    item = random.choice(shopping)
                    expenses.append(Expense(user=user, date=d, description=item[0], category='Shopping',
                                            amount=item[1], payment='Card'))

                # Bills in first week
                if day_off < len(bills):
                    item = bills[day_off]
                    expenses.append(Expense(user=user, date=d, description=item[0], category='Bills',
                                            amount=item[1], payment='Netbanking'))

                # Other random
                if day_off % 8 == 0:
                    item = random.choice(other)
                    expenses.append(Expense(user=user, date=d, description=item[0], category='Other',
                                            amount=item[1], payment='UPI'))

            # Learning expenses scattered
            for item in learning_exp:
                expenses.append(Expense(user=user, date=today - timedelta(days=random.randint(1, 25)),
                                        description=item[0], category='Learning', amount=item[1], payment='Card'))

            Expense.objects.bulk_create(expenses)
            self.stdout.write(self.style.SUCCESS(f'  {len(expenses)} expenses'))

        # ── LEARNING SESSIONS ─────────────────────────────────
        if not LearningSession.objects.filter(user=user).exists():
            sessions = [
                ('System Design - Load Balancers', 'YouTube', 2.5, 'Completed', 1),
                ('React Native deep linking', 'Online Course', 1.5, 'Completed', 1),
                ('Docker multi-stage builds', 'Documentation', 1.0, 'Completed', 2),
                ('TypeScript utility types', 'Online Course', 2.0, 'Completed', 3),
                ('PostgreSQL query tuning', 'Book', 1.5, 'In Progress', 3),
                ('AWS S3 presigned URLs', 'YouTube', 1.0, 'Completed', 4),
                ('Redis pub/sub patterns', 'Documentation', 0.5, 'Completed', 5),
                ('Next.js server actions', 'YouTube', 3.0, 'Completed', 5),
                ('Flutter Riverpod 2.0', 'Online Course', 2.0, 'In Progress', 6),
                ('Python FastAPI basics', 'Online Course', 1.5, 'Completed', 7),
                ('CI/CD GitHub Actions', 'Documentation', 1.0, 'Completed', 8),
                ('Tailwind + Framer Motion', 'YouTube', 1.5, 'Completed', 9),
                ('LLM prompt engineering', 'Podcast', 0.5, 'In Progress', 10),
                ('DynamoDB single table', 'Online Course', 2.0, 'On Hold', 12),
                ('Rust ownership basics', 'Book', 1.0, 'In Progress', 14),
                ('Figma auto layout', 'YouTube', 1.0, 'Completed', 16),
                ('GraphQL subscriptions', 'Documentation', 1.5, 'Completed', 18),
                ('Kubernetes Helm charts', 'Online Course', 2.5, 'In Progress', 20),
                ('WebSocket real-time apps', 'YouTube', 1.0, 'Completed', 22),
                ('Django Channels tutorial', 'Online Course', 2.0, 'On Hold', 25),
                ('System Design - CDNs', 'YouTube', 1.5, 'Completed', 27),
                ('Go concurrency patterns', 'Book', 1.0, 'In Progress', 28),
            ]
            objs = [LearningSession(user=user, date=today - timedelta(days=d),
                                     topic=t, source=s, hours=h, status=st)
                    for t, s, h, st, d in sessions]
            LearningSession.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} learning sessions'))

        # ── GOALS ──────────────────────────────────────────────
        if not Goal.objects.filter(user=user).exists():
            goals = [
                ('Emergency Fund 3L', 'Finance', 300000, 75000, 180, 'Building 6-month runway'),
                ('Learn System Design', 'Learning', 100, 42, 90, 'Targeting 100 hours total'),
                ('Side Project Launch', 'Career', 50, 38, 45, 'MVP for SaaS tool - 50 tasks'),
                ('Save for Europe Trip', 'Travel', 200000, 180000, 120, 'Paris + Switzerland 2 weeks'),
                ('Read 24 Books in 2025', 'Personal', 24, 9, 270, '2 books per month target'),
                ('6-pack abs by Dec', 'Personal', 100, 35, 200, 'Track workout consistency %'),
                ('Build Investment Portfolio', 'Finance', 500000, 220000, 365, 'Diversified - equity+debt+gold'),
                ('Learn Rust basics', 'Skill', 40, 8, 150, '40 hours Rust programming'),
            ]
            objs = [Goal(user=user, name=n, category=c, target=t, current=cur,
                         deadline=today + timedelta(days=d), notes=notes)
                    for n, c, t, cur, d, notes in goals]
            Goal.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} goals'))

        # ── SAVINGS ────────────────────────────────────────────
        if not SavingEntry.objects.filter(user=user).exists():
            savings = [
                ('Nifty 50 Index SIP', 'SIP', 5000, 'Zerodha', 0),
                ('HDFC FD 7.2% - 1yr', 'FD', 10000, 'HDFC Bank', 2),
                ('PPF Annual Deposit', 'PPF', 12500, 'SBI', 5),
                ('Sovereign Gold Bond', 'Gold', 3000, 'RBI', 7),
                ('Axis Bluechip SIP', 'SIP', 3000, 'Groww', 9),
                ('NPS Tier 1 Contribution', 'NPS', 5000, 'HDFC Pension', 12),
                ('ICICI RD Monthly', 'RD', 2000, 'ICICI Bank', 14),
                ('Kotak Savings Interest', 'Savings Account', 5000, 'Kotak', 16),
                ('Mirae Asset Large Cap SIP', 'SIP', 4000, 'Kuvera', 18),
                ('ELSS Tax Saver SIP', 'SIP', 2500, 'Groww', 20),
                ('Parag Parikh Flexi Cap', 'SIP', 3000, 'Zerodha', 22),
                ('Digital Gold Purchase', 'Gold', 1000, 'PhonePe', 25),
            ]
            objs = [SavingEntry(user=user, date=today - timedelta(days=d),
                                name=n, inv_type=t, amount=a,
                                monthly_income=85000, platform=p)
                    for n, t, a, p, d in savings]
            SavingEntry.objects.bulk_create(objs)
            self.stdout.write(self.style.SUCCESS(f'  {len(objs)} savings entries'))

        self.stdout.write(f'\n  Demo: {email} / Demo1234!')
        self.stdout.write(f'  Expenses:  {Expense.objects.filter(user=user).count()}')
        self.stdout.write(f'  Learning:  {LearningSession.objects.filter(user=user).count()}')
        self.stdout.write(f'  Goals:     {Goal.objects.filter(user=user).count()}')
        self.stdout.write(f'  Savings:   {SavingEntry.objects.filter(user=user).count()}')

    def _create_test_users(self):
        """Test users for verifying 2FA flow."""
        # Test user 1: has phone → needs email + SMS OTP
        u1, c1 = User.objects.get_or_create(
            email='test1@trackwise.in',
            defaults={'full_name': 'Test Phone User', 'phone': '9876500002'},
        )
        if c1:
            u1.set_password('Test1234!')
            u1.save()
            Profile.objects.create(user=u1, monthly_income=60000)
            Subscription.objects.create(user=u1, status='trial',
                                        trial_ends_at=timezone.now() + timedelta(days=7))
            self.stdout.write(self.style.SUCCESS('Created test1@trackwise.in (with phone)'))

        # Test user 2: no phone → needs only email OTP
        u2, c2 = User.objects.get_or_create(
            email='test2@trackwise.in',
            defaults={'full_name': 'Test Email User'},
        )
        if c2:
            u2.set_password('Test1234!')
            u2.save()
            Profile.objects.create(user=u2, monthly_income=50000)
            Subscription.objects.create(user=u2, status='trial',
                                        trial_ends_at=timezone.now() + timedelta(days=7))
            self.stdout.write(self.style.SUCCESS('Created test2@trackwise.in (email only)'))
