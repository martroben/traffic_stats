# external
import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def daily_results(data: pandas.DataFrame, motor_vehicle_title: str, bicycle_title: str):
    motor_vehicle_color = "#526a83"
    bicycle_color = "#a06177"
    # input column names
    n_harmed_bicycle = "n_harmed_bicycle"
    n_harmed_motor_vehicle = "n_harmed_motor_vehicle"
    n_harmed_bicycle_cumulative = "n_harmed_bicycle_cumulative"
    n_harmed_motor_vehicle_cumulative = "n_harmed_motor_vehicle_cumulative"

    daily_yaxis_max = 1.1 * max([max(data[n_harmed_bicycle]),
                                 max(data[n_harmed_motor_vehicle])])
    cumulative_yaxis_max = 1.1 * max([max(data[n_harmed_bicycle_cumulative]),
                                      max(data[n_harmed_motor_vehicle_cumulative])])
    xaxis_min = min(data["day"])
    xaxis_max = max(data["day"])

    figure = make_subplots(
        rows=3, cols=1,
        row_heights=[40, 5, 5],
        shared_xaxes=True,
        vertical_spacing=0.05)

    motor_vehicle_by_day_graph = go.Bar(
        name="participants in motor vehicle accidents per day",
        x=data["day"],
        y=data[n_harmed_motor_vehicle],
        marker=dict(
            color=motor_vehicle_color,
            line_color=motor_vehicle_color),
        showlegend=False)

    bicycle_by_day_graph = go.Bar(
        name="participants in bicycle accidents per day",
        x=data["day"],
        y=data[n_harmed_bicycle],
        marker=dict(
            color=bicycle_color,
            line_color=bicycle_color),
        showlegend=False)

    motor_vehicle_cumulative_graph = go.Scatter(
        name=motor_vehicle_title,
        x=data["day"],
        y=data[n_harmed_motor_vehicle_cumulative],
        line=dict(
            color=motor_vehicle_color,
            width=1),
        fill="tozeroy")

    bicycle_cumulative_graph = go.Scatter(
        name=bicycle_title,
        x=data["day"],
        y=data[n_harmed_bicycle_cumulative],
        line=dict(
            color=bicycle_color,
            width=1),
        fill="tozeroy")

    motor_vehicle_cumulative_highest = go.Scatter(
        x=[max(data["day"])],
        y=[max(data[n_harmed_motor_vehicle_cumulative])],
        mode="markers+text",
        marker=dict(
            color=motor_vehicle_color,
            size=8),
        text=[int(max(data[n_harmed_motor_vehicle_cumulative]))],
        textposition="middle right",
        showlegend=False,
        cliponaxis=False)

    bicycle_cumulative_highest = go.Scatter(
        x=[max(data["day"])],
        y=[max(data[n_harmed_bicycle_cumulative])],
        mode="markers+text",
        marker=dict(
            color=bicycle_color,
            size=8),
        text=[int(max(data[n_harmed_bicycle_cumulative]))],
        textposition="middle right",
        showlegend=False,
        cliponaxis=False)

    figure.add_trace(motor_vehicle_cumulative_graph, row=1, col=1)
    figure.add_trace(bicycle_cumulative_graph, row=1, col=1)
    figure.add_trace(motor_vehicle_cumulative_highest, row=1, col=1)
    figure.add_trace(motor_vehicle_by_day_graph, row=2, col=1)
    figure.add_trace(bicycle_by_day_graph, row=3, col=1)
    figure.add_trace(bicycle_cumulative_highest, row=1, col=1)

    figure.update_layout(
        bargap=0,
        autosize=False,
        # width=1000,
        height=800,
        plot_bgcolor="white",
        yaxis1_range=[0, cumulative_yaxis_max],
        yaxis2_range=[0, daily_yaxis_max],
        yaxis3_range=[0, daily_yaxis_max],
        xaxis1_range=[xaxis_min, xaxis_max],
        yaxis1_tickfont_size=10,
        yaxis2_tickfont_size=8,
        yaxis3_tickfont_size=8,
        legend=dict(
            yanchor="top",
            y=1.05,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0)"))
    figure.update_yaxes(gridcolor="lightgrey")

    figure.show()
