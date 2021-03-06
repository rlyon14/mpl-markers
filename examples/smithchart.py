
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import markerplot
from matplotlib import ticker
from rfnetwork import Sparam, format_smithchart, db20
from markerplot import interactive_subplots

dir_ = Path(__file__).parent

matplotlib.use('Qt4Agg') 

tga2598 = Sparam(dir_ / r'data/TGA2598-SM.s2p')
qpl9057 = Sparam(dir_ / r'data/QPL9057.s2p')

def yformat(x,y,mxd):
    return '{:.3f}'.format(mxd)

fig, ax1 = interactive_subplots(1, 1, figsize=(10,5), constrained_layout=True, yformat=yformat)


format_smithchart(ax1, admittance=False, vswr_cirlce=True, lines=[5, 2, 1, 0.5, 0.2, 0])

line = ax1.plot(np.real(tga2598.sdata[:,0,0]), np.imag(tga2598.sdata[:,0,0]), marker_xd=tga2598.freq/1e9, label='tga2598')
line = ax1.plot(np.real(qpl9057.sdata[:,0,0]), np.imag(qpl9057.sdata[:,0,0]), marker_xd=qpl9057.freq/1e9, label='qpl9057')



fig, ax = interactive_subplots(1, 1, figsize=(10,5), constrained_layout=True, show_xlabel=True)

ax.marker_link(ax1)
ax.grid(True)
ax.plot(tga2598.freq/1e9, db20(tga2598.sdata[:,0,0]), label='tga2598')
ax.plot(qpl9057.freq/1e9, db20(qpl9057.sdata[:,0,0]), label='qpl9057')

plt.show()
