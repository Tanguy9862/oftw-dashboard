from dash import dcc, Output, Input, State, clientside_callback, ClientsideFunction
import dash_mantine_components as dmc
from constants.ui import GITHUB


def make_modal() -> dmc.Modal:
    return dmc.Modal(
        id='modal-data-source',
        size='50%',
        title='Dashboard Methodology & Data Notes',
        styles={
            'root': {
                "boxShadow": "0px 6px 15px rgba(0, 0, 0, 0.1)"
            },
            'header': {
                'background-color': '#EDF2F7',
            },
            'content': {
                'background-color': '#f9fafb'
            }
        },
        children=[
            dmc.Text(
                "This dashboard provides an overview of One for the World’s (OFTW) key performance metrics, "
                "tracking financial performance, donor engagement, and recurring revenue growth. Data is aggregated "
                "and visualized to support monitoring of organizational goals across both fiscal and calendar periods.",
                c='dimmed',
                mt='md'
            ),
            dmc.Title(
                "Target Definition",
                order=3,
                c='#1f2937',
                mt='lg',
                mb='xs'
            ),
            dcc.Markdown(
                [
                    f"""
                    Annual targets are sourced directly from OFTW. Quarterly targets are derived using a data-informed methodology:
                    
                    - For each metric, the average share contributed by each quarter to the annual total was calculated based on complete historical years.
                    - Years with insufficient or incomplete data were excluded using volume-based thresholds to ensure reliability.
                    - Separate calculations were performed for **fiscal years (FY)** and **calendar years (CY)** to reflect seasonal patterns in donor behavior.
                    - These proportions were then applied to each annual target to produce custom quarterly benchmarks.
                    
                    The target generation process is fully documented in the `create_target_json.ipynb` notebook available in the [GitHub repository]({GITHUB}).
                    
                    """
                ],
                style={'color': '#334155'}
            ),

            dmc.Title(
                "Period Comparison Logic",
                order=3,
                c='#1f2937',
                mt='lg',
                mb='xs'
            ),
            dcc.Markdown(
                [
                    """
                    Comparative values are dynamically adapted based on the selected period:
                    
                    - When viewing a full year, metrics are compared to the same period in the previous year.
                    - When viewing a specific quarter, metrics are compared to:
                      - The same quarter in the previous year
                      - The previous quarter
                      - The current quarter
                    
                    This allows for both temporal benchmarking and trend detection.
                    """
                ],
                style={'color': '#334155'}
            ),

            dmc.Title(
                "Data Cleaning & Exclusions",
                order=3,
                c='#1f2937',
                mt='lg',
                mb='xs'
            ),
            dcc.Markdown(
                [
                    """
                    The following portfolios were excluded from all calculations:
                    
                    - `One for the World Discretionary Fund`
                    - `One for the World Operating Costs`
                    
                    Additional data preprocessing steps include:
                    - Filtering based on the selected year aggregation mode (fiscal vs. calendar)
                    - Dynamic recalculation of performance pace based on elapsed time in the selected period
                    - Deduplication of pledges and normalization of frequencies for consistent ARR calculations
                    """
                ],
                style={'color': '#334155'}
            ),

            dmc.Title(
                "Visual Encodings",
                order=3,
                c='#1f2937',
                mt='lg',
                mb='xs'
            ),
            dcc.Markdown(
                [
                    """
                    - **Color coding**: Metrics are visually categorized as On Track (green), Slightly Behind (gray), or Off Track (red), depending on their proximity to the expected pace.
                    - **Pace line**: A dotted line represents where performance should be at this point in the year, if progress were linear.
                    - **Target line**: A solid line indicates the final goal for the period.
                    """
                ],
                style={'color': '#334155'}
            ),

            dmc.Title(
                "Reproducibility & Transparency",
                order=3,
                c='#1f2937',
                mt='lg',
                mb='xs'
            ),
            dcc.Markdown(
                [
                    f"""
                    All preprocessing steps, target calculations, and metric logic are openly documented. For further details, refer to the source notebook and implementation code in the [GitHub repository]({GITHUB}).
                    """
                ],
                style={'color': '#334155'}
            ),
        ]
    )


clientside_callback(
    ClientsideFunction(namespace='clientside', function_name='toggle_modal_data_source'),
    Output('modal-data-source', 'opened'),
    Input('about-data-source', 'n_clicks'),
    State('modal-data-source', 'opened')
)
