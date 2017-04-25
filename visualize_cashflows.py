""" Produces web page with inputs for CPR curve shape and speed, weighted average maturity,
and original balance amount. Produces interactive Bokeh datatable with collateral amortization
along with charts for CPR and PSA curves as well as the total cash flow received each period."""


import warnings
from os.path import dirname, join

import numpy as np
import pandas as pd
from bokeh.layouts import widgetbox, layout
# from bokeh.io import output_file, show
from bokeh.models import NumeralTickFormatter, ColumnDataSource, CustomJS
from bokeh.models.tools import HoverTool
from bokeh.models.widgets import Button, Slider, DataTable, NumberFormatter, TableColumn, TextInput
from bokeh.plotting import figure, curdoc

warnings.filterwarnings('ignore')

import collateral_waterfall as cw
import prepayment_calcs as pc

colors = {
    1: 'red',
    2: 'blue',
    3: 'green',
    4: 'orange'
}

source = ColumnDataSource(data=dict(periods=[],
                                    psa_speed=[],
                                    cash_flow=[],
                                    beginning_balance=[],
                                    SMM=[],
                                    mortgage_payments=[],
                                    net_interest=[],
                                    prepayments=[],
                                    scheduled_principal=[],
                                    total_principal=[]))

cpr_curve_input = TextInput(title='CPR Curve Description', value='.2 ramp 6 for 30, 6')
psa_speed_slider = Slider(start=.1, end=5, step=.1, value=1, title='Prepay Curve Speed')
wam_slider = Slider(start=10, end=360, step=1, value=358, title='WAM')
original_balance_slider = Slider(start=1e6, end=1e9, step=1e6, value=400e6, title='Original balance')
calc_button = Button(label='Calculate')

download_button = Button(label="Download Datatable", button_type="success")
download_button.callback = CustomJS(args=dict(source=source),
                                    code=open(join(dirname(__file__), "download.js")).read())

inputbox1 = widgetbox([psa_speed_slider, wam_slider, original_balance_slider])
inputbox2 = widgetbox([cpr_curve_input, calc_button, download_button])
# for control in controls:
#    control.on_change('value', lambda attr, old, new: update())

wam = 358
window = range(1, wam + 1)

# PSA graph

psa_figure = figure(title='PSA speed', tools=['box_zoom', 'lasso_select', 'box_select', 'save', 'reset'])

for mult in np.linspace(0.25, 3, num=12):
    periods = []
    psa_speed = []

    for period in window:
        periods.append(period)
        psa_speed.append(pc.PSA(period) * mult)
    psa_figure.line(periods, psa_speed, name='PSA-{0:.2f}'.format(mult), alpha=0.3)

psa_figure.yaxis.formatter = NumeralTickFormatter(format='0%')

# Waterfall graphs

waterfall_figure = figure(title='Waterfall',
                          tools=['box_zoom', 'lasso_select', 'box_select', 'save', 'reset', HoverTool(tooltips=[
                              ('Month:', '@periods{int}'),
                              ('SMM:', '@SMM{0.00000}'),
                              ('Mortgage Payments:', '@mortgage_payments{"$,"}'),
                              ('Net Interest:', '@net_interest{"$,"}'),
                              ('Scheduled Principal:', '@scheduled_principal{"$,"}'),
                              ('Prepayments:', '@prepayments{"$,"}'),
                              ('Total Principal:', '@total_principal{"$,"}'),
                              ('Total Cash Flow:', '@cash_flow{"$,"}'),
                          ])])

psa_speeds = [1.0, 1.65]

columns = [
    TableColumn(field='periods', title='Month', formatter=NumberFormatter(format=',')),
    TableColumn(field='beginning_balance', title='Beginning Balance', formatter=NumberFormatter(format=',')),
    TableColumn(field='SMM', title='SMM', formatter=NumberFormatter(format='0.00000')),
    TableColumn(field='mortgage_payments', title='Mortgage Payments', formatter=NumberFormatter(format=',')),
    TableColumn(field='net_interest', title='Net Interest', formatter=NumberFormatter(format=',')),
    TableColumn(field='scheduled_principal', title='Scheduled Principal', formatter=NumberFormatter(format=',')),
    TableColumn(field='prepayments', title='Prepayments', formatter=NumberFormatter(format=',')),
    TableColumn(field='total_principal', title='Total Principal', formatter=NumberFormatter(format=',')),
    TableColumn(field='cash_flow', title='Total Cash Flow', formatter=NumberFormatter(format=',')),
]

waterfall_figure.x_range = psa_figure.x_range
waterfall_figure.xaxis.axis_label = 'Month of Payment'
waterfall_figure.yaxis.axis_label = 'Total Cash Flows ($)'
waterfall_figure.xaxis.formatter = NumeralTickFormatter(format='0')
waterfall_figure.yaxis.formatter = NumeralTickFormatter(format=',')

data_table = DataTable(source=source, columns=columns, fit_columns=True, width=1200, row_headers=False)

def update():
    """update() is called when the calculate button is pressed and refreshes the information in the datatable and charts
    corresponding to user the inputs."""

    cpr_curve = pc.cpr_curve_creator(cpr_curve_input.value)
    speed = psa_speed_slider.value
    wam = wam_slider.value
    bal = original_balance_slider.value

    source.data['index'] = []
    source.data['periods'] = []
    source.data['psa_speed'] = []
    source.data['cash_flow'] = list(np.zeros(wam))
    source.data['beginning_balance'] = list(np.zeros(wam))
    source.data['SMM'] = list(np.zeros(wam))
    source.data['mortgage_payments'] = list(np.zeros(wam))
    source.data['net_interest'] = list(np.zeros(wam))
    source.data['prepayments'] = list(np.zeros(wam))
    source.data['scheduled_principal'] = list(np.zeros(wam))
    source.data['total_principal'] = list(np.zeros(wam))

    window = range(1, wam + 1)
    print(window)
    for period in window:
        source.data['index'].append(period)
        source.data['periods'].append(period)
        source.data['psa_speed'].append(cpr_curve[period - 1] * speed)

    print(pd.DataFrame(data=[source.data['periods'], source.data['psa_speed']]).T.tail())
    psa_figure.line(x='periods', y='psa_speed', source=source, name='PSA-{0:.2f}'.format(mult), alpha=1,
                    color='red', legend='CPR Curve')

    waterfall = cw.create_waterfall(original_balance=bal, psa_speed=speed, wam=wam,
                                    cpr_description=cpr_curve_input.value)
    source.data['cash_flow'] = waterfall.cash_flow.tolist()
    source.data['beginning_balance'] = waterfall.beginning_balance.tolist()
    source.data['SMM'] = waterfall.SMM.tolist()
    source.data['mortgage_payments'] = waterfall.mortgage_payments.tolist()
    source.data['net_interest'] = waterfall.net_interest.tolist()
    source.data['prepayments'] = waterfall.prepayments.tolist()
    source.data['scheduled_principal'] = waterfall.scheduled_principal.tolist()
    source.data['total_principal'] = waterfall.total_principal.tolist()

    waterfall_figure.circle(x='periods', y='cash_flow', color='blue', source=source, legend='Total Cash Flow')

    # print(len(source.data['beginning_balance']), len(source.data['psa_speed']), len(source.data['cash_flow']))

# output_file('waterfalls.html')
#show(grid)

calc_button.on_click(update)

grid = layout([
    [inputbox1, inputbox2],
    [data_table],
    [psa_figure, waterfall_figure]])  # , sizing_mode='stretch_both')

update()

curdoc().add_root(grid)
