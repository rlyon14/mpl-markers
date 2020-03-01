from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QLabel, QSizePolicy, QSlider, QSpacerItem, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget, QStyleFactory, QGroupBox, QCheckBox)

from PyQt5 import QtWidgets, QtCore, QtGui
#from PyQt5.Qtgui import QImage
import numpy as np

from pathlib import Path
import sys

from time import time
import matplotlib.pyplot as plt
import markerplot
from markerplot import marker_default_params
import matplotlib
import io

import sys
import time
from pathlib import Path
import win32clipboard
from PIL import Image

import numpy as np
# from fbs_runtime.application_context.PyQt5 import ApplicationContext
from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5

from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

dir_ = Path(__file__).parent



class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self, nrows=1, ncols=1, **kwargs):
        matplotlib.use('Qt5Agg')

        self.qapp = QtWidgets.QApplication(sys.argv)
        
        super().__init__()

        self._main = QtWidgets.QWidget()
        
        self.setStyle(QStyleFactory.create('Fusion'))

        self.setCentralWidget(self._main)
        self.layout = QGridLayout(self._main)

        
        marker_kw = {}
        for k in marker_default_params.keys():
            if k in kwargs.keys():
                v = kwargs.pop(k)
                marker_kw[k] = v


        title = kwargs.pop('title', None)
        icon = kwargs.pop('icon', None)

        if icon != None:
            self.setWindowIcon(QtGui.QIcon(str(icon)))
        
        
        marker_kw['interactive'] = kwargs.pop('interactive', True)
        marker_kw['top_axes'] = kwargs.pop('top_axes', None)
        marker_kw['link_all'] = kwargs.pop('link_all', False)


        self.single_trace = kwargs.pop('single_trace', False)
    

        subplot_kw = kwargs.pop('subplot_kw', {})
        sharex = kwargs.pop('sharex', False)
        sharey = kwargs.pop('sharey', False)
        gridspec_kw = kwargs.pop('gridspec_kw', None)

        self.fig = plt.figure(**kwargs)
        
        self.ax = self.fig.subplots(nrows, ncols, squeeze=False, 
            sharex=False, 
            sharey=False, 
            subplot_kw =subplot_kw, 
            gridspec_kw=gridspec_kw)
        
        
        self.nrows = nrows
        self.ncols = ncols

    
        self.canvas = self.fig.canvas
        self.canvas.mpl_disconnect(self.canvas.manager.key_press_handler_id)
        
        self.canvas.manager.show = self._show
        self.layout.addWidget(self.canvas, 0,0, (self.nrows*self.ncols)+1, 1)
        
        self.toolbar = NavigationToolbar(self.canvas, self, coordinates=False)
        self.build_toolbar()

        self.addToolBar(self.toolbar)
        self.fig.canvas.toolbar = self.toolbar
        self.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.canvas.setFocus()

        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.white)
        self.setPalette(p)

        title = 'Figure {}'.format(self.fig.canvas.manager.num) if title == None else title
        self.setWindowTitle(title)

        self.fig.marker_enable(**marker_kw)
        self.fig.qapp = self.qapp
        self.fig.app = self
        self.draw_updates = False
        self.createTracesGroup()

    def add_toolbar_actions(self, *widgets, end=True):
        for icon_path, name, tooltip, action in widgets:

            icon = QtGui.QPixmap(str(icon_path))
            icon.setDevicePixelRatio(self.canvas._dpi_ratio)
            a = self.toolbar.addAction(QtGui.QIcon(icon), name, action)
            a.setToolTip(tooltip)

        if end:
            locLabel = QLabel("", self.toolbar)
            locLabel.setAlignment(
                    QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
            locLabel.setSizePolicy(
                QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Ignored))
            self.toolbar.addWidget(locLabel)

    def build_toolbar(self):
        
        self.toolbar.removeAction(self.toolbar._actions['configure_subplots'])
        self.toolbar.removeAction(self.toolbar._actions['forward'])
        self.toolbar.removeAction(self.toolbar._actions['back'])

        widgets = [(str(dir_  / 'icons/layout_large.png'), 'Layout', 'Apply Tight Layout', self.set_tight_layout),
                   (str(dir_  / 'icons/copy_large.png'), 'Copy', 'Copy To Clipboard', self.copy_figure),
                   (str(dir_  / 'icons/erase_large.png'), 'Delete', 'Remove All Markers', self.remove_all),
        ]

        self.add_toolbar_actions(*widgets, end=False)
        self.toolbar.addSeparator()
        
            
    def createCheckBoxLabel(self, label, size=14):
        r,g,b,a=self.palette().base().color().getRgbF()

        _figure=Figure(edgecolor=(r,g,b), facecolor=(r,g,b), dpi=100)

        _canvas=FigureCanvas(_figure)

        _figure.clear()
        text=_figure.suptitle(
            label,
            x=0.0,
            y=1.0,
            horizontalalignment='left',
            verticalalignment='top',
            size='small'
        )
        _canvas.draw()

        (x0,y0),(x1,y1)=text.get_window_extent().get_points()
        w=x1-x0; h=y1-y0
        
        _canvas.setFixedSize(w,h)
        return _canvas

    def createTracesGroup(self):
        self.traces = [(None, None)]*(self.nrows * self.ncols)
        for i in range(self.nrows):
            for j in range(self.ncols):
                layout = QGridLayout()
                layout.setAlignment(Qt.AlignLeft)
                 
                self.traces[i*self.ncols + j] = (QGroupBox("Axes {},{}".format(i,j)), layout)
                self.traces[i*self.ncols + j][0].setLayout(layout) 

    def update_traces_group(self, remove=True):

        self.traces_cb = [[]]*(self.nrows * self.ncols)
        self.draw_updates = False
        
        for i, ax in enumerate(self.ax.flatten()):
            row = 0
            for ax_shared in ax.get_shared_x_axes().get_siblings(ax):
                for l in ax_shared.lines:

                    label = l.get_label()
                    if label == '' or label[0] == '_':
                        continue

                    cb = CheckBox('')#QCheckBox('')
                    self.traces_cb[i].append((cb, l, label))
                    
                    cb.setChecked(True)

                    cb.stateChanged.connect(self.state_changed(ax_shared, l, cb, label))
                    if self.single_trace:
                        cb.setChecked(row==0)

                    qlabel = self.createCheckBoxLabel(label, size=14)
                    
                    layout = self.traces[i][1]
                    layout.addWidget(cb, row, 0)
                    layout.addWidget(qlabel, row, 1, alignment=Qt.AlignLeft)
                    
                    row += 1

                leg_loc = ax_shared.get_legend()._loc_real if ax_shared.get_legend() != None else 0
                ax_shared.legend(fontsize='small', loc=leg_loc)
        self.draw_updates = True

        added_traces = False
        for i, (tr, ly) in enumerate(self.traces):
            if len(self.traces_cb[i]) > 1:
                added_traces = True
                self.layout.addWidget(tr, i, 1)
        
        if added_traces:
            self.layout.addWidget(QGroupBox(), i+1,1)
            self.layout.setColumnStretch(0, 1)
            self.layout.setRowStretch(i+1, 1)


        # self.menu_scroll = QScrollArea(widgetResizable=False)
        # self.menu_scroll.setWidget(self.traces)

    def state_changed(self, ax, l, cb, label):

        def calluser():
            state = cb.isChecked()
            l.set_visible(state)
            if state:
                l.set_label(label)
            else:
                l.set_label('')

            leg_loc = ax.get_legend()._loc_real if ax.get_legend() != None else 0
            ax.legend(fontsize='small', loc=leg_loc)
        
            if self.draw_updates:
                self.canvas.draw()
        return calluser

    def remove_all(self):
        for ax in self.fig.axes:
            ax.marker_delete_all()
            for l_ax in ax.marker_linked_axes:
                l_ax.marker_delete_all()

        self.fig.canvas.draw()
        drawn = [self.fig]
        for ax in self.fig.axes:
            for l_ax in ax.marker_linked_axes:
                fig = l_ax.figure
                if fig not in drawn:
                    fig.canvas.draw()
                    drawn.append(fig)
    
    def set_tight_layout(self):
        self.fig.tight_layout()
        self.canvas.draw()

    def copy_figure(self):

        buf = io.BytesIO()
        self.fig.savefig(buf)

        image = Image.open(buf)
        output = io.BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()

        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        buf.close()
        

    def _show(self):
        
        self.update_traces_group(remove=False)

        self.show()
        
        #self.qapp.exec_()
        #self.qapp.show()
        
class CheckBox(QCheckBox):
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.nextCheckState()
        super(CheckBox, self).keyPressEvent(event)

class CanvasManager(object):
    def __init__(self, show_func):
        self._show = show_func
    def show(self):
        return self._show()


def interactive_subplots(nrows=1, ncols=1, **kwargs):
    app = PlotWindow(nrows, ncols, **kwargs)
    ax = np.array(app.ax)

    squeeze = kwargs.pop('squeeze', True)

    if squeeze:
        ax = ax.item() if ax.size == 1 else ax.squeeze()

    return app.fig, ax

if __name__ == "__main__":

    fig, ax = interactive_subplots(1,1, constrained_layout=True)

    t = np.linspace(0, 10, 101)
    ax.plot(t, np.sin(t), label='sin')
    ax.plot(t, np.cos(t), label='cos')
    
    fig, ax = interactive_subplots(2,1, link_all=True, show_xlabel=True)

    ax[0].plot(t, np.sin(t), label='sin')
    ax[1].plot(t, np.cos(t), label='cos')
    ax[1].plot(t, np.sin(t), label='cos')

    plt.show()