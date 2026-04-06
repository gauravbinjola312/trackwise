"""
Dashboard View — Runs all 24 rules and returns combined stats.

GET /api/v1/dashboard/          Full dashboard data (KPIs + charts + alerts)
GET /api/v1/dashboard/alerts/   Only the rule-engine alerts
GET /api/v1/dashboard/export/   Export all user data as JSON
"""
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from trackwise_backend.apps.expenses.models import Expense
from trackwise_backend.apps.learning.models import LearningSession
from trackwise_backend.apps.goals.models import Goal
from trackwise_backend.apps.savings.models import SavingEntry
from trackwise_backend.apps.expenses.serializers import ExpenseSerializer
from trackwise_backend.apps.learning.serializers import LearningSessionSerializer
from trackwise_backend.apps.goals.serializers import GoalSerializer
from trackwise_backend.apps.savings.serializers import SavingEntrySerializer
from trackwise_backend.utils.mixins import SuccessResponseMixin

logger = logging.getLogger('trackwise_backend')


# ═══════════════════════════════════════════════════════════════
#  RULE ENGINE — 24 transparent rules, pure Python
# ═══════════════════════════════════════════════════════════════

EXPENSE_LIMITS = {
    'Food':          {'warn': 30, 'danger': 45},
    'Entertainment': {'warn': 10, 'danger': 20},
    'Transport':     {'warn': 15, 'danger': 25},
    'Shopping':      {'warn': 10, 'danger': 20},
    'Learning':      {'min_pct': 5},
}


def run_rules(expenses, learning, goals, savings, days=30):
    """
    Runs all 24 rules against the last `days` of data.
    Returns list of insight dicts: { scope, sev, icon, tag, title, desc }
    """
    insights = []
    today    = date.today()
    cutoff   = today - timedelta(days=days)

    recent_exp  = [e for e in expenses  if e.date >= cutoff]
    recent_sav  = [s for s in savings   if s.date >= cutoff]

    # ── EXPENSE RULES ─────────────────────────────────────────
    total = sum(float(e.amount) for e in recent_exp) or 0
    cats  = {}
    for e in recent_exp:
        cats[e.category] = cats.get(e.category, 0) + float(e.amount)

    for cat, rule in EXPENSE_LIMITS.items():
        spent = cats.get(cat, 0)
        pct   = round(spent / total * 100) if total else 0

        if 'danger' in rule and pct >= rule['danger']:
            insights.append({
                'scope': 'expense', 'sev': 'red', 'icon': '🔴', 'tag': 'OVERSPEND',
                'title': f'{cat} is {pct}% of {days}-day spending',
                'desc':  f'Limit {rule["danger"]}%. Spent ₹{spent:,.0f}. Cut ₹{spent - total * rule["danger"] / 100:,.0f} to fix.',
            })
        elif 'warn' in rule and pct >= rule['warn']:
            insights.append({
                'scope': 'expense', 'sev': 'yellow', 'icon': '🟡', 'tag': 'WATCH',
                'title': f'{cat} at {pct}% of spending — near limit',
                'desc':  f'Max {rule["danger"]}%. Currently ₹{spent:,.0f}.',
            })

        if 'min_pct' in rule and pct < rule['min_pct'] and total > 0:
            insights.append({
                'scope': 'expense', 'sev': 'blue', 'icon': '💡', 'tag': 'INVEST MORE',
                'title': f'Only {pct}% on {cat.lower()} this month',
                'desc':  f'Aim for {rule["min_pct"]}%+ on {cat.lower()} for long-term growth.',
            })

    # R6: Delivery vs groceries
    delivery = sum(float(e.amount) for e in recent_exp
                   if e.category == 'Food' and any(k in e.description.lower()
                   for k in ['zomato','swiggy','restaurant','blinkit']))
    grocery  = sum(float(e.amount) for e in recent_exp
                   if e.category == 'Food' and any(k in e.description.lower()
                   for k in ['grocery','kirana','supermarket','dmart','vegetable']))
    if delivery > 0 and grocery > 0 and delivery > grocery * 1.5:
        insights.append({
            'scope': 'expense', 'sev': 'yellow', 'icon': '🍔', 'tag': 'FOOD HABIT',
            'title': 'Delivery spending more than groceries',
            'desc':  f'₹{delivery:,.0f} delivery vs ₹{grocery:,.0f} groceries. Cook 2 extra days/week.',
        })

    # R7: Subscription stack
    streaming = [e for e in recent_exp if e.category == 'Entertainment' and
                 any(k in e.description.lower() for k in ['netflix','prime','hotstar','spotify','zee5'])]
    if len(streaming) >= 3:
        sub_total = sum(float(e.amount) for e in streaming)
        insights.append({
            'scope': 'expense', 'sev': 'yellow', 'icon': '📺', 'tag': 'SUB STACK',
            'title': f'{len(streaming)} streaming subs — ₹{sub_total:,.0f}/mo',
            'desc':  f'Cancel 1–2 = ₹{sub_total * 12 * 0.4:,.0f}/year saved.',
        })

    # R8: Entertainment vs learning
    ent_amt  = cats.get('Entertainment', 0)
    lrn_amt  = cats.get('Learning', 0)
    if ent_amt > lrn_amt * 3 and ent_amt > 400:
        ratio = round(ent_amt / max(1, lrn_amt))
        insights.append({
            'scope': 'expense', 'sev': 'yellow', 'icon': '⚖️', 'tag': 'PRIORITIES',
            'title': f'{ratio}× more on entertainment than learning',
            'desc':  f'₹{ent_amt:,.0f} entertainment vs ₹{lrn_amt:,.0f} learning. Highest ROI switch.',
        })

    # ── LEARNING RULES ────────────────────────────────────────
    if learning:
        sorted_learn = sorted(learning, key=lambda r: r.date, reverse=True)
        last_date    = sorted_learn[0].date
        gap          = (today - last_date).days

        week_hrs  = sum(float(s.hours) for s in learning if (today - s.date).days <= 7)
        month_hrs = sum(float(s.hours) for s in learning if s.date >= cutoff)

        if gap >= 7:
            insights.append({
                'scope': 'learning', 'sev': 'red', 'icon': '📉', 'tag': 'LEARNING GAP',
                'title': f'No learning logged in {gap} days',
                'desc':  f'Last session: {last_date}. 7-day gap kills momentum.',
            })
        elif gap >= 3:
            insights.append({
                'scope': 'learning', 'sev': 'yellow', 'icon': '⏳', 'tag': 'SLOWING DOWN',
                'title': f'{gap} days since last learning session',
                'desc':  'Log at least every 2 days to stay consistent.',
            })

        if week_hrs < 3:
            insights.append({
                'scope': 'learning', 'sev': 'yellow', 'icon': '⏱', 'tag': 'LOW HOURS',
                'title': f'Only {week_hrs:.1f}h this week',
                'desc':  'Target 5–7h/week.',
            })
        elif week_hrs >= 7:
            insights.append({
                'scope': 'learning', 'sev': 'green', 'icon': '🔥', 'tag': 'ON TRACK',
                'title': f'{week_hrs:.1f}h this week!',
                'desc':  f'{month_hrs:.1f}h this month. Top percentile.',
            })

    # ── GOAL RULES ────────────────────────────────────────────
    for g in goals:
        pct   = g.pct_complete
        dl    = g.days_left
        daily = g.daily_required

        if g.is_overdue:
            insights.append({
                'scope': 'goal', 'sev': 'red', 'icon': '❌', 'tag': 'OVERDUE',
                'title': f'"{g.name}" overdue — {pct}% complete',
                'desc':  f'Expired {abs(dl)}d ago. Update deadline or revise.',
            })
        elif dl < 30 and pct < 70:
            insights.append({
                'scope': 'goal', 'sev': 'red', 'icon': '⚠️', 'tag': 'AT RISK',
                'title': f'"{g.name}" — {pct}% done, {dl}d left',
                'desc':  f'Need ₹{daily:,.0f}/day to finish on time.',
            })
        elif dl < 60 and pct < 50:
            insights.append({
                'scope': 'goal', 'sev': 'yellow', 'icon': '📅', 'tag': 'BEHIND PACE',
                'title': f'"{g.name}" — {pct}% done, {dl}d left',
                'desc':  'Pick up pace or revise your deadline.',
            })
        elif pct >= 80:
            insights.append({
                'scope': 'goal', 'sev': 'green', 'icon': '🏁', 'tag': 'ALMOST DONE',
                'title': f'"{g.name}" — {pct}%!',
                'desc':  f'Only ₹{float(g.target) - float(g.current):,.0f} to go!',
            })

    # ── SAVINGS RULES ─────────────────────────────────────────
    saved_total  = sum(float(s.amount) for s in recent_sav)
    with_income  = next((s for s in recent_sav if float(s.monthly_income) > 0), None)
    income       = float(with_income.monthly_income) if with_income else 0
    rate_pct     = round(saved_total / income * 100) if income else 0

    if income > 0:
        if rate_pct < 10:
            insights.append({
                'scope': 'savings', 'sev': 'red', 'icon': '🏦', 'tag': 'LOW SAVINGS',
                'title': f'Saving only {rate_pct}% of income',
                'desc':  f'Target 20% = ₹{income * 0.2:,.0f}/mo. You need ₹{income * 0.2 - saved_total:,.0f} more.',
            })
        elif rate_pct < 20:
            insights.append({
                'scope': 'savings', 'sev': 'yellow', 'icon': '💰', 'tag': 'SAVE MORE',
                'title': f'{rate_pct}% savings rate — target is 20%',
                'desc':  f'Increase by ₹{income * 0.2 - saved_total:,.0f} to hit target.',
            })
        else:
            insights.append({
                'scope': 'savings', 'sev': 'green', 'icon': '🌱', 'tag': 'GOOD RATE',
                'title': f'{rate_pct}% savings rate — above target!',
                'desc':  f'₹{saved_total * 12:,.0f}/year at this pace. Excellent.',
            })

    if savings and not recent_sav:
        insights.append({
            'scope': 'savings', 'sev': 'red', 'icon': '📭', 'tag': 'NO SAVINGS',
            'title': 'No savings logged this month',
            'desc':  'Even ₹500 into SIP adds up. Start today.',
        })

    if len(recent_sav) >= 3:
        types = set(s.inv_type for s in recent_sav)
        if len(types) == 1:
            insights.append({
                'scope': 'savings', 'sev': 'blue', 'icon': '🎯', 'tag': 'DIVERSIFY',
                'title': f'All investments in {list(types)[0]}',
                'desc':  'Spread across SIP + FD + Gold to reduce risk.',
            })

    # Sort: red first, then yellow, blue, green
    order = {'red': 0, 'yellow': 1, 'blue': 2, 'green': 3}
    return sorted(insights, key=lambda i: order.get(i['sev'], 4))


# ═══════════════════════════════════════════════════════════════
#  VIEWS
# ═══════════════════════════════════════════════════════════════

class DashboardView(SuccessResponseMixin, APIView):
    """
    GET /api/v1/dashboard/?days=30

    Returns everything the mobile app needs in one call:
    - KPI cards (6 metrics)
    - Category breakdown (donut chart data)
    - Bar chart data (you vs recommended)
    - Goals at a glance
    - All rule-engine alerts
    - Subscription status
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user  = request.user
        days  = int(request.query_params.get('days', 30))
        today = date.today()
        cutoff= today - timedelta(days=days)

        # Fetch all user data
        expenses = list(Expense.objects.filter(user=user).order_by('-date'))
        learning = list(LearningSession.objects.filter(user=user).order_by('-date'))
        goals    = list(Goal.objects.filter(user=user).order_by('deadline'))
        savings  = list(SavingEntry.objects.filter(user=user).order_by('-date'))

        # Period-filtered
        recent_exp = [e for e in expenses if e.date >= cutoff]
        recent_sav = [s for s in savings  if s.date >= cutoff]
        recent_lrn = [l for l in learning if l.date >= cutoff]

        # ── KPI Calculations ──────────────────────────────────
        total_spent = sum(float(e.amount) for e in recent_exp)
        cats        = {}
        for e in recent_exp:
            cats[e.category] = cats.get(e.category, 0) + float(e.amount)

        food_pct = round(cats.get('Food', 0) / total_spent * 100) if total_spent else 0
        lrn_hrs  = sum(float(s.hours) for s in recent_lrn)
        total_sav= sum(float(s.amount) for s in recent_sav)
        goal_avg = round(sum(g.pct_complete for g in goals) / len(goals)) if goals else 0

        # ── Alerts ────────────────────────────────────────────
        alerts    = run_rules(expenses, learning, goals, savings, days)
        red_count = sum(1 for a in alerts if a['sev'] == 'red')

        # ── Donut chart data ──────────────────────────────────
        chart_data = [
            {'category': cat, 'amount': round(amt, 2), 'pct': round(amt / total_spent * 100, 1) if total_spent else 0}
            for cat, amt in sorted(cats.items(), key=lambda x: -x[1])
        ]

        # ── Bar chart data (you vs recommended limits) ─────────
        bar_labels = ['Food', 'Entertainment', 'Transport', 'Shopping', 'Learning']
        bar_limits = [45, 20, 25, 20, 5]
        bar_data   = [
            {
                'label': lbl,
                'your_pct': round(cats.get(lbl, 0) / total_spent * 100, 1) if total_spent else 0,
                'limit_pct': lim,
            }
            for lbl, lim in zip(bar_labels, bar_limits)
        ]

        # ── Subscription status ───────────────────────────────
        sub_data = None
        try:
            sub = user.subscription
            sub_data = {
                'status':         sub.status,
                'is_active':      sub.is_active,
                'trial_days_left':sub.trial_days_left,
                'plan':           sub.plan,
                'paid_until':     sub.paid_until,
            }
        except Exception:
            pass

        return self.success({
            'period_days': days,
            'kpis': {
                'active_alerts':  red_count,
                'total_spent':    round(total_spent, 2),
                'food_pct':       food_pct,
                'learning_hours': round(lrn_hrs, 1),
                'saved_amount':   round(total_sav, 2),
                'goals_average':  goal_avg,
            },
            'charts': {
                'expense_breakdown': chart_data,
                'vs_recommended':    bar_data,
            },
            'goals_glance': [
                {
                    'id':          str(g.id),
                    'name':        g.name,
                    'category':    g.category,
                    'pct_complete':g.pct_complete,
                    'days_left':   g.days_left,
                    'status':      g.status,
                    'current':     float(g.current),
                    'target':      float(g.target),
                }
                for g in goals[:4]  # Top 4 for glance view
            ],
            'alerts':       alerts,
            'subscription': sub_data,
        })


class AlertsView(SuccessResponseMixin, APIView):
    """
    GET /api/v1/dashboard/alerts/?days=30
    Returns only the rule-engine alerts (lighter payload).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        days = int(request.query_params.get('days', 30))

        expenses = list(Expense.objects.filter(user=user))
        learning = list(LearningSession.objects.filter(user=user))
        goals    = list(Goal.objects.filter(user=user))
        savings  = list(SavingEntry.objects.filter(user=user))

        alerts = run_rules(expenses, learning, goals, savings, days)
        return self.success({
            'period_days': days,
            'total':       len(alerts),
            'reds':        sum(1 for a in alerts if a['sev'] == 'red'),
            'yellows':     sum(1 for a in alerts if a['sev'] == 'yellow'),
            'greens':      sum(1 for a in alerts if a['sev'] == 'green'),
            'alerts':      alerts,
        })


class ExportView(SuccessResponseMixin, APIView):
    """
    GET /api/v1/dashboard/export/
    Exports all user data as JSON (for backup / CSV generation).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return self.success({
            'exported_at': date.today().isoformat(),
            'user_email':  user.email,
            'expenses':    ExpenseSerializer(Expense.objects.filter(user=user), many=True).data,
            'learning':    LearningSessionSerializer(LearningSession.objects.filter(user=user), many=True).data,
            'goals':       GoalSerializer(Goal.objects.filter(user=user), many=True).data,
            'savings':     SavingEntrySerializer(SavingEntry.objects.filter(user=user), many=True).data,
        })
