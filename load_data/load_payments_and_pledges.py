import pandas as pd


def load_data() -> pd.DataFrame:
    df = pd.read_csv('data/payments_and_pledges.csv', parse_dates=['date'])
    df['month'] = pd.to_datetime(df['month']).dt.to_period('M')
    return df


# Load date range from data
df_payments_and_pledges = load_data()
