import numpy as np
from bokeh.io import output_file, show
from bokeh.models import NumeralTickFormatter
from bokeh.plotting import figure, gridplot

import collateral_waterfall as cw
import prepayment_calcs as pc

colors = {
    1: 'red',
    2: 'blue',
    3: 'green',
    4: 'orange'
}

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

line_counter = 0

for speed in psa_speeds:
    line_counter += 1
    x = []
    y = []
    for period in periods:
        x.append(period)
        y.append(pc.PSA(period) * speed)
    psa_figure.line(x, y, name='PSA-{0:.2f}'.format(mult), alpha=1, color=colors[line_counter])

    x = periods
    waterfall = cw.create_waterfall(psa_speed=speed, wam=358)
    y = waterfall.cash_flow.tolist()

    waterfall_figure.line(x, y, color=colors[line_counter])

waterfall_figure.x_range = psa_figure.x_range
waterfall_figure.xaxis.axis_label = 'Month of Payment'
waterfall_figure.yaxis.axis_label = 'Total Cash Flows ($)'
waterfall_figure.xaxis.formatter = NumeralTickFormatter(format='0')
waterfall_figure.yaxis.formatter = NumeralTickFormatter(format=',')

grid = gridplot([(psa_figure, waterfall_figure)])

output_file('waterfalls.html')
show(grid)
