from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QApplication, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
                             QLabel, QSizePolicy, QSlider, QSpacerItem, QPushButton, QScrollArea,
                             QVBoxLayout, QWidget, QStyleFactory, QGroupBox, QCheckBox, QAction, QComboBox)

from PySide2 import QtWidgets, QtCore, QtGui
import numpy as np

from pathlib import Path
import sys

from time import time
import matplotlib.pyplot as plt
import matplotlib
import io
import re

import markerplot
from markerplot import marker_default_params

import sys
import time
from pathlib import Path
import win32clipboard
from PIL import Image

import numpy as np
from matplotlib.backends.qt_compat import is_pyqt5

from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

dir_ = Path(__file__).parent

def hide_lines(*lines, state=True):
    for l in lines:
        l._i_hidden = state
        l.set_visible(not state)
        if not state:
            try:
                l.set_label(l._i_label)
            except:
                pass
        else:
            l._i_label = l.get_label()
            l.set_label('')
        

class InputDialog(QtWidgets.QMainWindow):
    def __init__(self, parent, select_callback):       
        super(InputDialog, self).__init__(parent)

        self._main = QtWidgets.QWidget()
        self.select_callback = select_callback
        
        #self.setStyle(QStyleFactory.create('Fusion'))

        self.setCentralWidget(self._main)
        layout = QGridLayout(self._main)

        layout.setAlignment(Qt.AlignLeft)

        self.data_select = [QComboBox() for i in parent.ax.flatten()]

        row = 0
        for i in range(parent.nrows):
            for j in range(parent.ncols):
                 
                label1 = QLabel("Axes {},{}".format(i,j))
                
                self.data_select[row].addItems(["Magnitude (dB)", "Phase (deg)", "Unwrapped Phase (deg)", "VSWR"])
                layout.addWidget(label1,          row, 0)
                layout.addWidget(self.data_select[row],  row, 1, 1,2)

                row += 1

        okbutton = QPushButton("Apply")
        okbutton.clicked.connect(self.select_apply)
        okbutton.setDefault(True)
        cancelbutton = QPushButton("Cancel")
        cancelbutton.clicked.connect(self.select_cancel)

        layout.addWidget(okbutton,          2, 1)
        layout.addWidget(cancelbutton,   2, 2)

        layout.setSpacing(5)

        self.setLayout(layout)
        
        self.setWindowTitle('Set Data Format')

    def select_apply(self):
        values = [str(ds.currentText()) for ds in self.data_select]
        self.select_callback(values)
        self.close()

    def select_cancel(self):
        self.close()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.select_station()
        super().keyPressEvent(event)

class PlotWindow(QtWidgets.QMainWindow):
    def __init__(self, nrows=1, ncols=1, **kwargs):
        matplotlib.use('Qt5Agg')

        
        #QtWidgets.QApplication(sys.argv)
        qapp = QtWidgets.QApplication.instance()
        if qapp is None:
            qapp = QtWidgets.QApplication(sys.argv)

        self.qapp = qapp
        
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
        self._drop_event_handler = None

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
                   (str(dir_  / 'icons/autoscale.png'), 'Autoscale', 'Autoscale Y-axis', self.autoscale_all),
                   (str(dir_  / 'icons/autoscale.png'), 'Set Data Format', 'Set Data Format', self.set_data_format),
                   
        ]

        self.add_toolbar_actions(*widgets, end=False)
        self.toolbar.addSeparator()
    
    def add_drop_event_handler(self, handler):
        self._drop_event_handler = handler
        
        if self._drop_event_handler != None:
            self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
            
        if e.mimeData().hasText():
            text = e.mimeData().text()
            m = re.search(r's\d+p$', text)
            if m != None:
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()
            
    def dropEvent(self, e):
        text = e.mimeData().text()
        self._drop_event_handler(text)
            
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

                

    def update_traces_group(self):

        self.traces_cb = [[] for i in range(self.nrows * self.ncols)]

        self.draw_updates = False
        
        
        for i, ax in enumerate(self.ax.flatten()):
            row = 1
            layout = self.traces[i][1]
            #for ax_shared in ax.get_shared_x_axes().get_siblings(ax):
            for l in ax.lines:
                try:
                    label = l._i_label
                except:
                    label = l.get_label()

                if len(label) and label[0] == '_':
                    continue

                y = l.get_ydata()
                y = np.where(np.isinf(y), np.nan, y)
                l.ymin, l.ymax  = np.nanmin(y), np.nanmax(y)

                cb = CheckBox('')
                self.traces_cb[i].append((cb, l, label))
                
                try:
                    if l._i_hidden:
                        cb.setChecked(False)
                    else:
                        cb.setChecked(True)
                except:
                    cb.setChecked(True)

                cb.stateChanged.connect(self.state_changed(ax, l, cb, label))
                if self.single_trace:
                    cb.setChecked(row==0)

                qlabel = self.createCheckBoxLabel(label, size=14)
                
                layout.addWidget(cb, row, 0)
                layout.addWidget(qlabel, row, 1, alignment=Qt.AlignLeft)
                
                row += 1

            leg_loc = ax.get_legend()._loc_real if ax.get_legend() != None else 0
            ax.legend(fontsize='small', loc=leg_loc)

        self.draw_updates = True

        added_traces = False
        self.cb_all = {}
        for i, (tr, ly) in enumerate(self.traces):
        
            cb = CheckBox('')

            layout = self.traces[i][1]
            layout.addWidget(cb, 0, 0)

            ax = self.ax.flatten()[i]
            cb.stateChanged.connect(self.state_changed(ax, None, cb, None))
            self.cb_all[id(ax._top_axes)] = cb

            if len(self.traces_cb[i]) <= 1:
                cb.hide()

            if len(self.traces_cb[i]) > 0:
                added_traces = True
                self.layout.addWidget(tr, i, 1)
        
        if added_traces:
            self.layout.addWidget(QGroupBox(), i+1,1)
            self.layout.setColumnStretch(0, 1)
            self.layout.setRowStretch(i+1, 1)


    def scale_ylim_visible(self, axes):

        miny, maxy = np.inf, -np.inf
        for l in axes.lines:
            if not l.get_visible():
                continue
            
            miny = l.ymin if l.ymin < miny else miny
            maxy = l.ymax if l.ymax > maxy else maxy

        if np.all(np.isfinite([miny, maxy])):
            pad = (maxy - miny)/20
            max_y = maxy + pad
            min_y = miny - pad
            axes.set_ylim([min_y, max_y])


    def update_all_cb(self, ax):
        idx = list(self.ax.flatten()).index(ax._top_axes)
        ax_cb = self.traces_cb[idx]
        checks = np.zeros(len(ax_cb))
        for i, cb in enumerate(ax_cb):
            checks[i] = int(cb[0].isChecked())

        self.draw_updates = False
        if np.all(checks):
            self.cb_all[id(ax._top_axes)].setCheckState(Qt.CheckState.Checked)
        elif np.any(checks):
            self.cb_all[id(ax._top_axes)].setCheckState(Qt.CheckState.PartiallyChecked)
        else:
            self.cb_all[id(ax._top_axes)].setCheckState(Qt.CheckState.Unchecked)
        self.draw_updates = True
                
    def state_changed(self, ax, l, cb, label):

        def calluser():
            leg_loc = ax.get_legend()._loc_real if ax.get_legend() != None else 0
            state = cb.isChecked()
            state = cb.checkState()
            
            if l == None:
                idx = list(self.ax.flatten()).index(ax)
                ax_cb = self.traces_cb[idx]
                if self.draw_updates:
                    self.draw_updates = False
                    if state == Qt.CheckState.PartiallyChecked:
                        cb.setCheckState(Qt.CheckState.Checked)
                    
                    for i, (cbn, ln, labeln) in enumerate(ax_cb):
                        
                        cbn.setChecked(state)

                    self.draw_updates = True


            else:
                if self.draw_updates:
                    self.update_all_cb(ax)
                #l.set_visible(state)
                hide_lines(*[l], state=not state)


            if self.draw_updates:
                ax._top_axes.draw_lines_markers()
        

        return calluser
    
    def set_data_format(self):
        dialog = InputDialog(self.fig.app, self.change_data_format)
        dialog.show()

    def change_data_format(self, values):
        for i, ax in enumerate(self.ax.flatten()):
            value = values[i]
            ax.clear()
            self._data_format_handler(ax, value)
        self.fig.canvas.draw()

    def add_data_format_handler(self, func):
        self._data_format_handler = func

    def autoscale_all(self):
        for ax in self.ax.flatten():
            leg_loc = ax.get_legend()._loc_real if ax.get_legend() != None else 0
            self.scale_ylim_visible(ax)
            ax.legend(fontsize='small', loc=leg_loc)
        self.fig.canvas.draw()

    def remove_all(self):
        for ax in self.fig._top_axes:
            ax.marker_delete_all()
            ax.draw_lines_markers()
            for l_ax in ax.marker_linked_axes:
                l_ax.marker_delete_all()
                l_ax.draw_lines_markers()
    
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
        for ax in self.ax.flatten():
            hide_lines(*ax.lines, state=False)

        self.update_traces_group()

        self.show()
        
        plt.close(self.fig)
        
class CheckBox(QCheckBox):
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.nextCheckState()
        super(CheckBox, self).keyPressEvent(event)


def interactive_subplots(nrows=1, ncols=1, **kwargs):
    app = PlotWindow(nrows, ncols, **kwargs)
    ax = np.array(app.ax)

    squeeze = kwargs.pop('squeeze', True)

    if squeeze:
        ax = ax.item() if ax.size == 1 else ax.squeeze()

    return app.fig, ax

