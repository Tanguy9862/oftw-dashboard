from load_data.load_payments_and_pledges import df_payments_and_pledges

# Year min and max
YEAR_MIN, YEAR_MAX = df_payments_and_pledges.year.min(), df_payments_and_pledges.year.max()

# Date and time constants
today = df_payments_and_pledges['date'].max()
MONTH_ORDER_FY = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
MONTH_ORDER_CY = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Frequency multiplier used to compute ARR
FREQ_MULTIPLIER = {
    "Monthly": 12,
    "Quarterly": 4,
    "Annually": 1,
    "Semi-Monthly": 24
}
