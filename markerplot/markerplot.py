
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.lines import Line2D
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
import gorilla
import matplotlib

class Marker(object):
    def __init__(self, axes, xd, yd, showXline=True, showYdot=True, xdisplay=None, smithchart=False, show_xlabel=True, xreversed=False):
        self.axes = axes
        self.xreversed = xreversed
        self.smithchart = smithchart
        self.show_xlabel = show_xlabel
        self.showXline = False if smithchart else showXline
        self.showYdot = showYdot
        self.xline = None
        self.xdisplay = xdisplay if isinstance(xdisplay, (list, np.ndarray)) else []

        self.data2display = self.axes.transData.transform
        self.display2data = self.axes.transData.inverted().transform
        self.data2axes = self.axes.transLimits.transform
        self.axes2data = self.axes.transLimits.inverted().transform
        self.axes2display = self.axes.transAxes.transform
        self.display2axes = self.axes.transAxes.inverted().transform

        #self.lines = list(self.axes._datalines)
        self.lines = []
        for l in self.axes.lines:
            if (l not in self.axes.marker_ignorelines):
                self.lines.append(l)

        self.ydot = [None]*len(self.lines)
        self.ytext = [None]*len(self.lines)
        self.xidx = None
        self.renderer = self.axes.figure.canvas.get_renderer()
        self.ytext_loc = []
        self.ytext_space = None
        self.xlen = 0
        if (len(self.lines) < 1):
            raise RuntimeError()

        self.createMarker(xd, yd)

    def _find_xidx(self, xd, yd=None):
        mline, xidx, mdist = None, 0, np.inf
        if (yd == None or self.showXline):
            mline = self.lines[0]
            xidx = (np.abs(mline.get_xdata()-xd)).argmin()
        else:
            for l in self.lines:
                xl, yl = l.get_xdata(), l.get_ydata()

                dist = (xl - xd)**2 + (yl-yd)**2	## array of distances (squared) of every point on the line from the point xd, yd
                xidx_l, mdist_l = np.argmin(dist), np.min(dist)   ## index and distance of the point on the line with the closest distance to xd, yd
                if mdist_l < mdist:
                    mline, xidx, mdist  = l, xidx_l, mdist_l
        return mline, xidx

    def createMarker(self, xd, yd=None):
        #print(xd, yd)
        mline, self.xidx = self._find_xidx(xd, yd)
        xd, yd = mline.get_xdata()[self.xidx], mline.get_ydata()[self.xidx]	
        xa, ya = self.data2axes((xd, yd))
        #print(xa, ya , self.xidx)

        if self.showXline:
            boxparams = dict(boxstyle='round', facecolor='black', edgecolor='black', alpha=0.7)
            self.xline = self.axes.axvline(xd, linewidth=0.5, color='r')
            self.axes.marker_ignorelines.append(self.xline)

            txt = self.xdisplay[self.xidx] if len(self.xdisplay) > 0  else '{:.3f}'.format(xd) 
            if (self.show_xlabel):
                self.xtext = self.axes.text(xa, 0, txt, color='white', transform=self.axes.transAxes, fontsize=8, verticalalignment='center', bbox=boxparams)
                xtext_dim = self.xtext.get_window_extent(self.renderer)

                x1 = self.display2axes((xtext_dim.x0, xtext_dim.y0))[0]
                x2 = self.display2axes((xtext_dim.x1, xtext_dim.y1))[0]
                #print(x1, x2)
                self.xlen = (x2-x1)/2
                self.xtext.set_position((xa-self.xlen, 0))
        
        self.yloc =[]
        xloc = []
        for i, l in enumerate(self.lines):
            xd, yd = l.get_xdata()[self.xidx], l.get_ydata()[self.xidx]	
            xa, ya = self.data2axes((xd, yd))
            boxparams = dict(facecolor='black', edgecolor=l.get_color(), linewidth=1.6, boxstyle='round', alpha=0.7)
            
            if self.smithchart and len(self.xdisplay) > 0:
                label = '{:0.3f}'.format(self.xdisplay[self.xidx]) if isinstance(self.xdisplay[self.xidx], float) else self.xdisplay[self.xidx]
            else:
                label = '{:0.3f}'.format(yd) #if self.labels[i] != None else '{:0.3f}'.format(yd)
            self.ytext[i] = self.axes.text(xa+0.01, ya, label ,color='white', fontsize=8, transform = self.axes.transAxes, verticalalignment='center', bbox=boxparams)
            ytext_dim = self.ytext[i].get_window_extent(self.renderer)
            y1 = self.display2axes((ytext_dim.x0, ytext_dim.y0))[1]
            y2 = self.display2axes((ytext_dim.x1, ytext_dim.y1))[1]
            self.ylen = (y2-y1)*1.8

            #print(ytext_dim)
            self.yloc.append(ya)

            if self.showYdot:
                self.ydot[i] = Line2D([xd], [yd], linewidth=10, color=l.get_color(), markersize=10)
                self.ydot[i].set_marker('.')
                self.ydot[i].set_linestyle(':')
                self.axes.add_line(self.ydot[i])
                self.axes.marker_ignorelines.append(self.ydot[i])

            xloc.append(xa)
        self.space_ylabels(xloc)

    def space_ylabels(self, xa):
        ylabels = list(self.ytext)
        zipped = zip(self.yloc, ylabels, xa)
        zipped_sorted  = sorted(zipped, key=lambda x: x[0])
        yloc, ylabels, xa = zip(*zipped_sorted)

        yloc = list(yloc)
        for i, y in enumerate(yloc):
            if i >= len(yloc) -1:
                break
            ovl = (yloc[i+1] - self.ylen/2) - (y + self.ylen/2)
            if ovl < 0:
                yloc[i] -= abs(ovl)/2
                yloc[i+1] += abs(ovl)/2
                for j in range(i-1, -1, -1):
                    ovl = (yloc[j+1] - self.ylen/2) - (yloc[j] + self.ylen/2)
                    if ovl < 0:
                        yloc[j] -= abs(ovl)

        for i, y in enumerate(yloc):
            ylabels[i].set_position((xa[i]+0.01, y))
        self.yloc = yloc

    def moveToIdx(self, xidx):
        self.xidx = xidx
        xd = self.lines[0].get_xdata()[self.xidx]
        xa, ya = self.data2axes((xd, 0))
        if self.showXline:
            self.xline.set_xdata([xd, xd])
            if self.show_xlabel:
                self.xtext.set_position((xa-self.xlen, 0))
                txt = self.xdisplay[self.xidx] if len(self.xdisplay) > 0  else '{:.3f}'.format(xd) 
                self.xtext.set_text(txt)

        self.yloc = []
        xloc = []
        for i, l in enumerate(self.lines):
            xd, yd = l.get_xdata()[self.xidx], l.get_ydata()[self.xidx]	
            xa, ya = self.data2axes((xd, yd))
            self.ytext[i].set_position((xa+0.01, ya))
            if self.smithchart and len(self.xdisplay) > 0:
                label = '{:0.3f}'.format(self.xdisplay[self.xidx]) if isinstance(self.xdisplay[self.xidx], float) else self.xdisplay[self.xidx]
            else:
                label = '{:0.3f}'.format(yd) #if self.labels[i] != None else '{:0.3f}'.format(yd)
            self.yloc.append(ya)
            self.ytext[i].set_text(label)
            if self.showYdot:
                self.ydot[i].set_data([xd], [yd])
            dim = self.ytext[i].get_window_extent(renderer=self.renderer)
            xloc.append(xa)
        
        self.space_ylabels(xloc)

    def move_to_point(self, xd, yd):
        self.mline, self.xidx = self._find_xidx(xd, yd)
        self.moveToIdx(self.xidx)

    def shiftMarker(self, direction):
        xlen = len(self.lines[0].get_xdata())
        direction = -direction if self.xreversed else direction
        nxidx = self.xidx -1 if direction < 0 else self.xidx +1
        if (nxidx >= xlen):
            nxidx = xlen-1
        elif (nxidx <= 0):
            nxidx = 0
        self.xidx = nxidx

        self.moveToIdx(self.xidx)

    def remove(self):
        if self.showXline:
            if self.show_xlabel:
                self.xtext.set_visible(False)
            idx = self.axes.lines.index(self.xline)
            self.axes.lines.pop(idx)
        for i, l in enumerate(self.lines):		
            idx = self.axes.lines.index(self.ydot[i])
            self.axes.lines.pop(idx)
            idx = self.ytext[i].set_visible(False)

    def contains_event(self, event):
        for ym in self.ytext:
            contains, attrd = ym.contains(event)
            if (contains):
                return True
        return False

class MarkerManager(object):
    def __init__(self, fig):
        self.fig = fig

        self.move = None
        self.shift_is_held = False
        self.active_marker = None

        self.cidclick = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.cidpress = self.fig.canvas.mpl_connect('key_press_event', self.onkey_press)
        self.cidbtnrelease = self.fig.canvas.mpl_connect('key_release_event', self.onkey_release)
        self.cidmotion = self.fig.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.cidbtnrelease = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)

    def get_event_marker(self, axes, event):
        for m in axes.markers:
            if m.contains_event(event):
                return m
        return None

    def onkey_release(self, event):
        if event.key == 'shift':
            self.shift_is_held = False

    def onkey_press(self, event):
        axes = event.inaxes

        if self.active_marker == None or axes == None:
            return
        elif event.key == 'shift':
            self.shift_is_held = True
        elif(event.key == 'left'):
            self.active_marker.shiftMarker(-1)
        elif(event.key == 'right'):
            self.active_marker.shiftMarker(1)
        elif(event.key == 'delete'):
            self.active_marker = axes.delete_marker(self.active_marker)
        self.fig.canvas.draw()

    def onmotion(self, event):
        xd = event.xdata
        yd = event.ydata
        axes = event.inaxes
        if axes == None or axes != self.move or self.active_marker == None:
            return
        
        self.active_marker.move_to_point(xd, yd)
        self.fig.canvas.draw()

    def onrelease(self, event):
        self.move = None

    def onclick(self, event):
        xd = event.xdata
        yd = event.ydata
        axes = event.inaxes
        if (axes == None):
            return
        self.move = axes

        m = self.get_event_marker(axes, event)

        if (m == None and (self.active_marker == None or self.shift_is_held == True)):
            self.active_marker = axes.add_marker(xd, yd)
        elif (m != None): 
            self.active_marker = m
        elif (self.active_marker != None):
            self.active_marker.move_to_point(xd, yd)
        else:
            return
        
        self.fig.canvas.draw()
        return

def add_marker(self, x, y=None):
    ## get axes marker settings
    params = self.marker_params
    new_marker = Marker(self.axes, x, y, **params)#, smithchart=self.smithchart, xdisplay=self.xDisplay, show_xlabel=self.show_xlabel)
    self.markers.append(new_marker)
    return new_marker

def delete_marker(self, marker):
    idx = self.markers.index(marker)
    marker.remove()
    self.markers.pop(idx)
    return self.markers[-1] if len(self.markers) > 0 else None

def set_marker_params(self, **kwargs):
    self.marker_params.update(**kwargs)
    
def enable_dynamic_markers(self, **kwargs):
    self._eventmanager = MarkerManager(self)
    for ax in self.axes:
        ax.grid(linewidth=0.5, linestyle='-')
        ax.markers =[]
        ax.marker_params = dict(**kwargs)
        ax.marker_ignorelines = []
    
        patch = gorilla.Patch(ax.__class__, 'add_marker', add_marker)
        gorilla.apply(patch)

        patch = gorilla.Patch(ax.__class__, 'delete_marker', delete_marker)
        gorilla.apply(patch)


