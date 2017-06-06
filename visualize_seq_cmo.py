"""WORK IN PROGRESS"""



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

wam = 360
window = range(1, wam + 1)

collateral_source = ColumnDataSource()

bonds_source = ColumnDataSource()

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


# Waterfall graphs

collateral_waterfall_figure = figure(title='Collateral',
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

bond_waterfall_figure = figure(title='Bonds',tools=['box_zoom', 'lasso_select', 'box_select', 'save', 'reset'])

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

data_table = DataTable(source=source, columns=columns, fit_columns=True, width=1200, row_headers=False)

def update():
    """update() is called when the calculate button is pressed and refreshes the information in the datatable and charts
    corresponding to user the inputs."""

    cpr_curve = pc.cpr_curve_creator(cpr_curve_input.value)
    speed = psa_speed_slider.value
    wam = wam_slider.value
    bal = original_balance_slider.value

    collateral_waterfall = ColumnDataSource(cw.create_waterfall(original_balance=bal, psa_speed=speed, wam=wam,
                                    cpr_description=cpr_curve_input.value))

    collateral_waterfall_figure.patch(x='periods',
                                        y='cash_flow',
                                        color='lightblue',
                                        source=collateral_waterfall_figure,
                            size=1)
    waterfall_figure.line(xs='periods', y='cash_flow', color='blue', source=source, legend='Total Cash Flow')

    waterfall_figure.x_range = psa_figure.x_range
    waterfall_figure.xaxis.axis_label = 'Month of Payment'
    waterfall_figure.yaxis.axis_label = 'Total Cash Flows ($)'
    waterfall_figure.xaxis.formatter = NumeralTickFormatter(format='0')
    waterfall_figure.yaxis.formatter = NumeralTickFormatter(format=',')
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
