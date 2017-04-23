import numpy as np
from bokeh.layouts import widgetbox, gridplot
# from bokeh.io import output_file, show
from bokeh.models import NumeralTickFormatter, ColumnDataSource
from bokeh.models.widgets import Button
from bokeh.models.widgets import Slider
from bokeh.plotting import figure, curdoc

import collateral_waterfall as cw
import prepayment_calcs as pc

colors = {
    1: 'red',
    2: 'blue',
    3: 'green',
    4: 'orange'
}

psa_slider = Slider(start=.1, end=5, step=.1, value=1, title='PSA')
wam_slider = Slider(start=10, end=360, step=1, value=358, title='WAM')
original_balance_slider = Slider(start=1e6, end=1e9, step=1e6, value=400e6, title='Original balance')
calc_button = Button(label='Calculate')

controls = [psa_slider, wam_slider, original_balance_slider, calc_button]
# for control in controls:
#    control.on_change('value', lambda attr, old, new: update())

wam = 358
periods = range(1, wam + 1)

# PSA graph

psa_figure = figure(title='PSA speed')
for mult in np.linspace(0.25, 3, num=12):
    x = []
    y = []

    for period in periods:
        x.append(period)
        y.append(pc.PSA(period) * mult)
    psa_figure.line(x, y, name='PSA-{0:.2f}'.format(mult), alpha=0.3)

psa_figure.yaxis.formatter = NumeralTickFormatter(format='0%')

# Waterfall graphs

waterfall_figure = figure(title='Waterfall')

psa_speeds = [1.0, 1.65]
source = ColumnDataSource(data=dict(periods=[], psa_speed=[], cash_flow=[]))


def update():
    source.data['periods'] = []
    source.data['psa_speed'] = []
    source.data['cash_flow'] = []

    speed = psa_slider.value
    wam = wam_slider.value
    bal = original_balance_slider.value

    periods = range(1, wam + 1)

    for period in periods:
        source.data['periods'].append(period)
        source.data['psa_speed'].append(pc.PSA(period) * speed)
    psa_figure.line(x='periods', y='psa_speed', source=source, name='PSA-{0:.2f}'.format(mult), alpha=1, color='red')

    waterfall = cw.create_waterfall(original_balance=bal, psa_speed=speed, wam=wam)
    source.data['cash_flow'] = waterfall.cash_flow.tolist()

    waterfall_figure.line(x='periods', y='cash_flow', color='blue', source=source)

    print(len(source.data['periods']), len(source.data['psa_speed']), len(source.data['cash_flow']))

waterfall_figure.x_range = psa_figure.x_range
waterfall_figure.xaxis.axis_label = 'Month of Payment'
waterfall_figure.yaxis.axis_label = 'Total Cash Flows ($)'
waterfall_figure.xaxis.formatter = NumeralTickFormatter(format='0')
waterfall_figure.yaxis.formatter = NumeralTickFormatter(format=',')

# output_file('waterfalls.html')
#show(grid)

calc_button.on_click(update)

inputs = widgetbox(*controls)

grid = gridplot([inputs], [psa_figure, waterfall_figure])

update()

curdoc().add_root(grid)
