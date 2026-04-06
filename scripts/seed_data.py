#!/usr/bin/env python
"""
Seed 500 users with realistic sample data for load testing.
Run: python scripts/seed_data.py
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackwise_backend.settings.development')
django.setup()

import random
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from faker import Faker

from trackwise_backend.apps.accounts.models import User, Profile
from trackwise_backend.apps.expenses.models import Expense
from trackwise_backend.apps.learning.models import LearningSession
from trackwise_backend.apps.goals.models import Goal
from trackwise_backend.apps.savings.models import SavingEntry
from trackwise_backend.apps.subscriptions.models import Subscription

fake = Faker('en_IN')

EXPENSE_TEMPLATES = [
    ('Zomato Order',    'Food',         200, 600,  'UPI'),
    ('Swiggy Dinner',   'Food',         150, 500,  'UPI'),
    ('Groceries',       'Food',         400, 1500, 'Cash'),
    ('Uber Cab',        'Transport',    80,  400,  'UPI'),
    ('Rapido Bike',     'Transport',    30,  150,  'UPI'),
    ('Netflix',         'Entertainment',199, 199,  'Card'),
    ('Amazon Prime',    'Entertainment',299, 299,  'Card'),
    ('Hotstar',         'Entertainment',299, 299,  'Card'),
    ('Udemy Course',    'Learning',     399, 999,  'Card'),
    ('Books',           'Learning',     200, 500,  'Card'),
    ('Electricity Bill','Bills',        800, 1500, 'Netbanking'),
    ('Internet Bill',   'Bills',        500, 800,  'Netbanking'),
    ('Clothing',        'Shopping',     500, 3000, 'Card'),
    ('Electronics',     'Shopping',     1000,5000, 'Card'),
    ('Restaurant Lunch','Food',         200, 600,  'UPI'),
]

LEARNING_TOPICS = [
    ('React Native',    'Online Course'),
    ('Python Basics',   'Online Course'),
    ('System Design',   'YouTube'),
    ('DSA',             'Online Course'),
    ('Atomic Habits',   'Book'),
    ('Deep Work',       'Book'),
    ('Startup Stories', 'Podcast'),
    ('AWS Basics',      'Documentation'),
    ('Machine Learning','Online Course'),
    ('SQL Advanced',    'Online Course'),
]

GOAL_TEMPLATES = [
    ('Emergency Fund',  'Finance',  50000,  100000),
    ('Europe Trip',     'Travel',   100000, 200000),
    ('New Laptop',      'Finance',  60000,  120000),
    ('Bike Fund',       'Finance',  50000,  150000),
    ('MBA Prep',        'Learning', 20000,  80000),
    ('Startup Fund',    'Business', 200000, 500000),
]

SAVINGS_TEMPLATES = [
    ('Nifty 50 SIP',   'SIP',    3000, 10000),
    ('HDFC FD',        'FD',     5000, 50000),
    ('PPF',            'PPF',    2000, 5000),
    ('Gold ETF',       'Gold',   1000, 5000),
    ('NPS',            'NPS',    2000, 5000),
    ('Savings Account','Savings Account', 500, 2000),
]


def past_date(days_back):
    return date.today() - timedelta(days=random.randint(0, days_back))


def future_date(days_forward):
    return date.today() + timedelta(days=random.randint(30, days_forward))


def seed_user(i):
    """Create one fully seeded user."""
    email = f'user{i}@trackwise.test'

    if User.objects.filter(email=email).exists():
        return None

    user = User.objects.create_user(
        email=email,
        password='Password123!',
        full_name=fake.name(),
    )

    income = random.choice([40000, 50000, 60000, 80000, 100000, 120000, 150000])

    Profile.objects.create(
        user=user,
        monthly_income=Decimal(income),
        currency='INR',
    )

    Subscription.objects.create(
        user=user,
        status=random.choice(['trial', 'active', 'trial', 'active']),
        plan=random.choice(['monthly', 'yearly']),
        trial_ends_at=timezone.now() + timedelta(days=random.randint(-5, 14)),
        paid_until=timezone.now() + timedelta(days=random.randint(0, 365)) if random.random() > 0.3 else None,
    )

    # Expenses — 15-40 in last 30 days
    num_expenses = random.randint(15, 40)
    expenses = []
    for _ in range(num_expenses):
        tmpl = random.choice(EXPENSE_TEMPLATES)
        expenses.append(Expense(
            user=user,
            date=past_date(30),
            description=tmpl[0],
            category=tmpl[1],
            amount=Decimal(random.randint(tmpl[2], tmpl[3])),
            payment=tmpl[4],
            notes='',
        ))
    Expense.objects.bulk_create(expenses)

    # Learning sessions — 4-12
    num_learning = random.randint(4, 12)
    sessions = []
    for _ in range(num_learning):
        topic, source = random.choice(LEARNING_TOPICS)
        sessions.append(LearningSession(
            user=user,
            date=past_date(30),
            topic=topic,
            source=source,
            hours=Decimal(random.choice([0.5, 1, 1.5, 2, 2.5, 3])),
            status=random.choice(['In Progress', 'In Progress', 'Completed', 'On Hold']),
            notes='',
        ))
    LearningSession.objects.bulk_create(sessions)

    # Goals — 2-4
    num_goals = random.randint(2, 4)
    goals = []
    for tmpl in random.sample(GOAL_TEMPLATES, num_goals):
        target  = random.randint(tmpl[2], tmpl[3])
        current = random.randint(0, target)
        goals.append(Goal(
            user=user,
            name=tmpl[0],
            category=tmpl[1],
            target=Decimal(target),
            current=Decimal(current),
            deadline=future_date(365),
            notes='',
        ))
    Goal.objects.bulk_create(goals)

    # Savings — 2-5
    num_savings = random.randint(2, 5)
    savings = []
    for tmpl in random.sample(SAVINGS_TEMPLATES, num_savings):
        savings.append(SavingEntry(
            user=user,
            date=past_date(30),
            name=tmpl[0],
            inv_type=tmpl[1],
            amount=Decimal(random.randint(tmpl[2], tmpl[3])),
            monthly_income=Decimal(income),
            platform=random.choice(['Zerodha', 'Groww', 'HDFC', 'Axis', 'SBI', 'Govt.']),
            notes='',
        ))
    SavingEntry.objects.bulk_create(savings)

    return user


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    print(f'\n🌱 Seeding {count} test users...\n')

    created = 0
    for i in range(1, count + 1):
        user = seed_user(i)
        if user:
            created += 1
            if created % 10 == 0:
                print(f'   → {created}/{count} users created...')

    total = User.objects.count()
    print(f'\n✅ Done! Created {created} new users.')
    print(f'   Total users in DB: {total}')
    print(f'\n   Login with: user1@trackwise.test / Password123!')


if __name__ == '__main__':
    main()
