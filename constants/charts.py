from constants.colors import BORDER_COLOR, LEGEND_COLOR, HEADER_COLOR

FIG_CONFIG = {"displayModeBar": False}
HEIGHT_METRIC_BAR_CHART = 60
BAR_CORNER_RADIUS = 4
BAR_WIDTH = 0.55
DEFAULT_PADDING = dict(pad=7, t=0, b=0, l=0, r=0)
CUSTOM_FONT = {
    'size': 14,
    'color': HEADER_COLOR,
    'family': "Inter, sans-serif"
}

HOVERLABEL_TEMPLATE = dict(
    bgcolor='rgba(255, 255, 255, 1)',
    bordercolor=BORDER_COLOR,
    font=dict(
        color=LEGEND_COLOR
    )
)
