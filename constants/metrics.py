from utils.metrics_engine import AmountMetric, CountMetric, RateMetric, ARRMetric

# Financial Performance metrics
financial_performance_metrics = [
    AmountMetric("Money Moved", slug='money_moved'),
    AmountMetric("Counterfactual MM", slug='counterfactual_mm', use_counterfactual=True),
]

# Donor Engagement metrics
engagement_metrics = [
    CountMetric("Total Active Donors", slug='total_active_donors', target_col="donor_id", status_to_filter=['Active donor', 'One-Time'], unit=" donors"),
    CountMetric("Total Active Pledges", slug='total_active_pledges', target_col="donor_id", status_to_filter=["Active donor"], unit=" donors"),
    CountMetric("All Pledges", slug='all_pledges', target_col="donor_id", status_to_filter=["Active donor", "Pledged donor"], unit=" donors"),
    CountMetric("Future Pledges", slug='future_pledges', target_col="donor_id", status_to_filter=["Pledged donor"], unit=" donors"),
]

# Revenue Projection (ARR) metrics
arr_metrics = [
    ARRMetric("All ARR", slug='all_arr', status_to_filter=['Active donor', 'Pledged donor']),
    ARRMetric("Active ARR", slug='active_arr', status_to_filter=['Active donor']),
    ARRMetric("Future ARR", slug='future_arr', status_to_filter=['Pledged donor'])
]

# Attrition Metrics
attrition_metrics = [
    RateMetric("Pledge Attrition Rate", slug='pledge_attrition_rate',
               status_to_filter=["Payment failure", "Churned donor"], is_attrition_metric=True),
    # RateMetric("Monthly Attrition", status_to_filter=["Payment failure", "Churned donor"], is_attrition_metric=True),
]

all_metrics = [*financial_performance_metrics, *engagement_metrics, *arr_metrics, *attrition_metrics]

# Mapping for breakdown categories
BREAKDOWN_OPTIONS_MAPPING = {
    'platform': 'payment_platform',
    'chapter': 'chapter_type',
    'channel': 'donor_chapter',
    'recurring': 'recurring_flag'
}

ONE_TIME_FREQUENCY = ['One-Time', 'Unspecified']