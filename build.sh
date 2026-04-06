#!/usr/bin/env bash
set -o errexit
pip install -r requirements-render.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.count() == 0:
    from django.core.management import call_command
    call_command('seed_data')
    print('Demo data seeded!')
else:
    print(f'Database has {User.objects.count()} users, skipping seed.')
"