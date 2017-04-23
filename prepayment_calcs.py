import numpy as np
from bokeh.io import output_file, show
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure


def SMM(CPR):
    return 1 - ((1 - CPR) ** (1 / 12))


def CPR(SMM):
    return 1 - ((1 - SMM) ** 12)


def PSA(month):
    if month <= 30:
        return month * 0.002
    else:
        return .06


if __name__ == "__main__":
    output_file('psa.html')
    hover = HoverTool(tooltips=[
        ('Mortgage Age', '$x'),
        ('Annual CPR', '$y')
    ])
    p = figure(title="PSA speeds", tools=[hover])
    periods = range(1, 361)

    for mult in np.linspace(0.5, 1.5, num=3):
        x = []
        y = []

        for period in periods:
            x.append(period)
            y.append(PSA(period) * mult)
        p.line(x, y, name='PSA-{0:.2f}'.format(mult))
    show(p)
