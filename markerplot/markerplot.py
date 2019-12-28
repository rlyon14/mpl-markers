
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from time import time
from threading import Timer, Semaphore


class Marker(object):
    
    def __init__(self, axes, xd, yd, idx=None):
        
        self.axes = axes 

        ## marker will inherit these parameters from axes, ignoring params from linked axes
        self.show_xline = axes.marker_params['show_xline']
        self.show_xlabel = axes.marker_params['show_xlabel']
        self.xformat = axes.marker_params['xformat']
        self.xreversed = axes.marker_params['xreversed']
        self.xmode = axes.marker_params['xmode']
        self.index_mode = axes.marker_params['index_mode']

        self.height_ylabel = 0
        self.width_ylabel = 0
        
       # self.xd_dimension

        #self.data2display = self.axes.transData.transform
        #self.display2data = self.axes.transData.inverted().transform
        #self.data2axes = self.axes.transLimits.transform
        #self.axes2data = self.axes.transLimits.inverted().transform

        scale_func = {'log': np.log10, 'linear': lambda x: x}

        ## future matplotlib versions (and maybe past versions) might keep the tranform functions synced with the scale.
        ## for 3.1.1 we have to do this manually
        def data2axes(ax, point):
            xscale = ax.get_xscale()
            yscale = ax.get_yscale()

            assert xscale in scale_func, 'x-axes scale: {} not supported'.format(xscale)
            assert yscale in scale_func, 'y-axes scale: {} not supported'.format(yscale)

            xd = scale_func[xscale](point[0])
            yd = scale_func[yscale](point[1])

            return ax.transLimits.transform((xd,yd))

        self.data2axes = data2axes
        self.axes2display = self.axes.transAxes.transform
        self.display2axes = self.axes.transAxes.inverted().transform

        ## set ylabel_gap to 8 display units, convert to axes coordinates
        self.ylabel_gap = self.display2axes((8,0))[0] - self.display2axes((0,0))[0]

        self.lines = []

        ## keep track of all lines we want to add markers to
        for l in self.axes.lines:
            if (l not in self.axes.marker_ignorelines):      
                self.lines.append((self.axes, l))

        ## get lines from any shared axes
        for ax in self.axes.get_shared_x_axes().get_siblings(self.axes):
            if ax == self.axes:
                continue
            for l in ax.lines:
                if (l not in ax.marker_ignorelines) and (l not in self.axes.marker_ignorelines):
                    self.lines.append((ax,l))
        
        self.ydot = [None]*len(self.lines)
        self.ytext = [None]*len(self.lines)
        self.xdpoint = None
        self.xidx = [0]*len(self.lines)
        self.renderer = self.axes.figure.canvas.get_renderer()
        self.line_xbounds = [None]*len(self.lines)

        if (len(self.lines) < 1):
            raise RuntimeError('Markers cannot be added to axes without data lines.')
        self.create(xd, yd, idx=idx)

    ## TODO: find nearest using axes or display coordinates, not data coordinates
    def find_nearest_xdpoint(self, xd, yd=None):
        mline, xdpoint, mdist = None, 0, np.inf

        for ax, l in self.lines:
            xl, yl = l.get_xdata(), l.get_ydata()

            if yd==None or self.xmode:
                dist = (xl - xd)**2
            else:
                dist = (xl - xd)**2 + (yl-yd)**2
            xidx_l, mdist_l = np.argmin(dist), np.min(dist)  
            
            if mdist_l < mdist:
                mline, xdpoint, mdist  = l, l.get_xdata()[xidx_l], mdist_l
        return mline, xdpoint

    def create(self, xd, yd=None, idx=None):
        
        mline, self.xdpoint = self.find_nearest_xdpoint(xd, yd)

        ## vertical x line
        boxparams = dict(boxstyle='round', facecolor='black', edgecolor='black', alpha=0.7)
        self.xline = self.axes.axvline(self.xdpoint, linewidth=0.5, color='r')
        self.axes.marker_ignorelines.append(self.xline)

        ## x label
        self.xtext = self.axes.text(0, 0, '0', color='white', transform=self.axes.transAxes, fontsize=8, verticalalignment='center', bbox=boxparams)
        self.xtext.set_zorder(20)

        ## ylabels and ydots for each line
        for i, (ax,l) in enumerate(self.lines):
    
            boxparams = dict(facecolor='black', edgecolor=l.get_color(), linewidth=1.6, boxstyle='round', alpha=ax.marker_params['alpha'])
            self.ytext[i] = ax.text(0, 0, '0' ,color='white', fontsize=8, transform = ax.transAxes, verticalalignment='center', bbox=boxparams)

            self.ydot[i] = Line2D([0], [0], linewidth=10, color=l.get_color(), markersize=10)
            self.ydot[i].set_marker('.')
            self.ydot[i].set_linestyle(':')
            ax.add_line(self.ydot[i])
            self.axes.marker_ignorelines.append(self.ydot[i])
            ax.marker_ignorelines.append(self.ydot[i])
            
            if not ax.marker_params['show_dot']:
                self.ydot[i].set_visible(False)
                self.ydot[i].set_zorder(0)
            self.line_xbounds[i] = np.min(l.get_xdata()), np.max(l.get_xdata())

        ## compute height of ylabels, for now we assume the width and height are 
        ## identical, need to fix this to allow differnt label sizes for each line.
        ytext_dim = self.ytext[0].get_window_extent(self.renderer)
        x1, y1 = self.display2axes((ytext_dim.x0, ytext_dim.y0))
        x2, y2 = self.display2axes((ytext_dim.x1, ytext_dim.y1))
        self.width_ylabel = np.abs(x2-x1)*1.8
        self.height_ylabel = (y2-y1)*1.8

        ## compute height of xlabel
        xtext_dim = self.xtext.get_window_extent(self.renderer)
        x1, y1 = self.display2axes((xtext_dim.x0, xtext_dim.y0))
        x2, y2 = self.display2axes((xtext_dim.x1, xtext_dim.y1))
        self.height_xlabel = (y2-y1)*1.8

        ## move objects to current point
        self.move_to_point(xd, yd, idx=idx)

        ## set visibility
        if not self.show_xlabel:
            self.xtext.set_visible(False)
        if not self.show_xline:
            self.xline.set_visible(False)

    ## space over y dimension if overlapped
    def space_labels(self, xa, ya):
        ylabels = list(self.ytext)
        zipped = zip(ya, ylabels, xa)
        zipped_sorted  = sorted(zipped, key=lambda x: x[0])
        yloc, ylabels, xloc = zip(*zipped_sorted)

        yloc = list(yloc)
        for i, y in enumerate(yloc):
            x_label_ovl = 0
            if i == 0:
                x_label_ovl = (yloc[i] - self.height_ylabel/2) - self.height_xlabel
                if x_label_ovl < 0 and self.show_xlabel:
                    yloc[i] += abs(x_label_ovl)
                    y = yloc[i]

            if i >= len(yloc) -1:
                break

            yovl = (yloc[i+1] - self.height_ylabel/2) - (y + self.height_ylabel/2)
            xovl = -1 #np.abs(xloc[i+1] - xloc[i])

            if (yovl < 0) and (xovl <= self.width_ylabel):
                if x_label_ovl < 0:
                    yloc[i+1] += abs(yovl)
                else:
                    yloc[i] -= abs(yovl)/2
                    yloc[i+1] += abs(yovl)/2
                for j in range(i-1, -1, -1):
                    yovl = (yloc[j+1] - self.height_ylabel/2) - (yloc[j] + self.height_ylabel/2)
                    if yovl < 0:
                        yloc[j] -= abs(yovl)

        for i, y in enumerate(yloc):
            ylabels[i].set_position((xloc[i]+self.ylabel_gap, y))


    def move_to_point(self, xd, yd=None, idx=None):
        mline, self.xdpoint = self.find_nearest_xdpoint(xd, yd)

        if not self.index_mode:
            for i, (ax,l) in enumerate(self.lines):
                self.xidx[i] = np.argmin(np.abs(l.get_xdata()-self.xdpoint))
                if l == mline:
                    self.xdpoint = l.get_xdata()[self.xidx[i]]
        else:
            if idx == None:
                idx = np.argmin(np.abs(mline.get_xdata()-self.xdpoint))
            for i, (ax,l) in enumerate(self.lines):
                self.xidx[i] = idx
            self.xdpoint = mline.get_xdata()[self.xidx[0]]
        
        ## vertical line placement
        self.xline.set_xdata([self.xdpoint, self.xdpoint])

        xa, ya = self.data2axes(self.axes, (self.xdpoint, 0))

        ## xlabel text
        if self.xformat != None:
            txt = self.xformat(self.xdpoint)
        else:
            txt = '{:.3f}'.format(self.xdpoint) 

        self.xtext.set_text(txt)

        ## xlabel placement
        xtext_dim = self.xtext.get_window_extent(self.renderer)
        x1 = self.display2axes((xtext_dim.x0, xtext_dim.y0))[0]
        x2 = self.display2axes((xtext_dim.x1, xtext_dim.y1))[0]
        xlen = (x2-x1)/2

        self.xtext.set_position((xa-xlen, self.height_xlabel/2))

        xloc = []
        yloc = []
        for i, (ax,l) in enumerate(self.lines):
            self.ytext[i].set_visible(True)
            self.ydot[i].set_visible(True)

            if not self.index_mode:
                ## turn off ylabel and dot if ypoint is out of bounds
                if (self.xdpoint > self.line_xbounds[i][1]) or (self.xdpoint < self.line_xbounds[i][0]):
                    self.ytext[i].set_visible(False)
                    self.ydot[i].set_visible(False)

            ## ylabel and dot position
            xd, yd = l.get_xdata()[self.xidx[i]], l.get_ydata()[self.xidx[i]]

            xa, ya = self.data2axes(ax, (xd, yd))
            xloc.append(xa)
            yloc.append(ya)

            if (not np.isfinite(yd)):
                self.ytext[i].set_visible(False)
                self.ydot[i].set_visible(False)

            else:
                self.ytext[i].set_position((xa+self.ylabel_gap, ya))
                self.ydot[i].set_data([xd], [yd])

                ## ylabel text
                if ax.marker_params['yformat'] != None:
                    txt = ax.marker_params['yformat'](xd, yd, self.xidx[i])
                else:
                    txt = '{:0.3f}'.format(yd)

                self.ytext[i].set_text(txt)
        
        self.space_labels(xloc, yloc)


    def shift(self, direction):
        direction = -direction if self.xreversed else direction
        xmax, xmin = -np.inf, np.inf

        if self.index_mode:
            xlen = len(self.lines[0][1].get_xdata())
            nxidx = self.xidx[0] -1 if direction < 0 else self.xidx[0] +1
            if (nxidx >= xlen):
                nxidx = xlen-1
            elif (nxidx <= 0):
                nxidx = 0
            self.move_to_point(self.lines[0][1].get_xdata()[nxidx])
            return

        line = None
        step_sizes = np.array([0.0]*len(self.lines), dtype='float64')
        if direction > 0:
            xloc = np.array([np.inf]*len(self.lines))
        else:
            xloc = np.array([-np.inf]*len(self.lines))

        for i, (ax,l) in enumerate(self.lines):
            xdata = l.get_xdata()

            if direction > 0:
                
                if (self.xidx[i] +1) < len(xdata):
                    step_sizes[i] = xdata[self.xidx[i] +1] - xdata[self.xidx[i]]
                    xloc[i] = xdata[self.xidx[i]]

            else:
                if (self.xidx[i] -1) >= 0:
                    step_sizes[i] = xdata[self.xidx[i]] - xdata[self.xidx[i] -1]
                    xloc[i] = xdata[self.xidx[i]]
    
        step_size = np.max(step_sizes)
        if direction > 0:
            l_idx = np.argmin(xloc)
            if np.min(xloc) < np.inf:
                new_xpoint = self.lines[l_idx][1].get_xdata()[self.xidx[l_idx]] + step_size
                self.move_to_point(new_xpoint)
        else:
            l_idx = np.argmax(xloc)
            if np.max(xloc) > -np.inf:
                new_xpoint = self.lines[l_idx][1].get_xdata()[self.xidx[l_idx]] - step_size
                self.move_to_point(new_xpoint)

    def remove(self):

        self.xtext.set_visible(False)
        idx = self.axes.lines.index(self.xline)
        self.axes.lines.pop(idx)

        for i, (ax,l) in enumerate(self.lines):		
            idx = ax.lines.index(self.ydot[i])
            ax.lines.pop(idx)
            idx = self.ytext[i].set_visible(False)

    def contains_event(self, event):
        contains, attrd = self.xtext.contains(event)
        if (contains):
            return True
            
        for ym in self.ytext:
            contains, attrd = ym.contains(event)
            if (contains):
                return True
        return False

    def set_animated(self, state):
        self.xline.set_animated(state)
        self.xtext.set_animated(state)
        for i, (ax,l) in enumerate(self.lines):
            self.ydot[i].set_animated(state)
            self.ytext[i].set_animated(state)

    ## assumes the canvas region has already been restored
    def draw(self):
        self.axes.draw_artist(self.xline)
        for i, (ax,l) in enumerate(self.lines):
            self.ydot[i].axes.draw_artist(self.ydot[i])
            self.ytext[i].axes.draw_artist(self.ytext[i])
        self.axes.draw_artist(self.xtext)

        blit_axes = []
        for i, (ax,l) in enumerate(self.lines):
            if ax in blit_axes: continue
            ax.figure.canvas.blit(ax.bbox)


class MarkerManager(object):
    def __init__(self, fig, top_axes=None):
        self.fig = fig

        if top_axes == None:
            self.top_axes = []
        elif not isinstance(top_axes, (tuple, list, np.ndarray)):
            self.top_axes = [top_axes]
        else:
            self.top_axes = top_axes

        for ax in self.top_axes:
            self.axes_to_top(ax)

        self.move = None
        self.shift_is_held = False 
        self.last_release = [None, 0]
        self.last_press = [None, 0]
        self.valid_press = False

        self.press_max_seconds = 0.05
        self.key_released_timer = None
        self.key_pressed = False
        self.zoom = False

        self.cidclick = self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.cidpress = self.fig.canvas.mpl_connect('key_press_event', self.onkey_press)
        self.cidbtnrelease = self.fig.canvas.mpl_connect('key_release_event', self.onkey_release)
        self.cidmotion = self.fig.canvas.mpl_connect('motion_notify_event', self.onmotion)
        self.cidbtnrelease = self.fig.canvas.mpl_connect('button_release_event', self.onrelease)

    def axes_to_top(self, axes):
        max_zorder = 0
        for ax in axes.get_shared_x_axes().get_siblings(axes):
            if ax.get_zorder() > max_zorder:
                max_zorder = ax.get_zorder()
        axes.set_zorder(max_zorder+1)
        axes.patch.set_visible(False)
        
    def move_linked(self, axes, xd, yd):
        axes.marker_active.move_to_point(xd, yd)
        for ax in axes.marker_linked_axes:
            ax.marker_active.move_to_point(xd, yd, idx=axes.marker_active.xidx[0])

    def add_linked(self, axes, xd, yd):
        marker = axes.marker_add(xd, yd)  
        for ax in axes.marker_linked_axes:
            ax.marker_add(xd, yd, idx=marker.xidx[0])  

        self.make_linked_active(axes, marker)

    def shift_linked(self, axes, direction):
        axes.marker_active.shift(direction)
        for ax in axes.marker_linked_axes:
            ax.marker_active.shift(direction)
        
    def delete_linked(self, axes):
        new_marker = axes.marker_delete(axes.marker_active)
        for ax in axes.marker_linked_axes:
            ax.marker_delete(ax.marker_active)

        self.make_linked_active(axes, new_marker)

        if axes.marker_active != None:
            axes.marker_active.draw()
            for ax in axes.marker_linked_axes:
                ax.marker_active.draw()

    def make_linked_active(self, axes, marker):
        if axes.marker_active != None:
            axes.marker_active.set_animated(False)

        for ax in axes.marker_linked_axes:
            if ax.marker_active != None:
                ax.marker_active.set_animated(False)

        axes.marker_active = marker
        if (marker != None):
            axes.marker_active.set_animated(True)
            idx = axes.markers.index(axes.marker_active)
            for ax in axes.marker_linked_axes:
                ax.marker_active = ax.markers[idx]
                ax.marker_active.set_animated(True)
        else:
            for ax in axes.marker_linked_axes:
                ax.marker_active = None

        self.draw_all()
        axes._draw_background = axes.figure.canvas.copy_from_bbox(axes.bbox)
        for ax in axes.marker_linked_axes:
            ax._draw_background = ax.figure.canvas.copy_from_bbox(ax.bbox)

    def draw_all(self):
        self.fig.canvas.draw()
        drawn = [self.fig]
        for ax in self.fig.axes:
            ax._draw_background = ax.figure.canvas.copy_from_bbox(ax.bbox)
            for l_ax in ax.marker_linked_axes:
                fig = l_ax.figure
                l_ax._draw_background = ax.figure.canvas.copy_from_bbox(ax.bbox)
                if fig not in drawn:
                    fig.canvas.draw()
                    drawn.append(fig)

    def draw_linked(self, axes):
        ## set active marker on each axes to animated
        axes.figure.canvas.restore_region(axes._draw_background)
        axes.marker_active.draw()
        for ax in axes.marker_linked_axes:
            ax.figure.canvas.restore_region(ax._draw_background)
            ax.marker_active.draw()


    def get_event_marker(self, axes, event):
        for m in axes.markers:
            if m.contains_event(event):
                return m
        return None

    def get_event_axes(self, event):
        plt.figure(self.fig.number)
        if plt.get_current_fig_manager().toolbar.mode != '':
            self.zoom = True
        if self.zoom:
            return None

        axes = event.inaxes
        if axes in self.fig.axes:
            for ax in axes.get_shared_x_axes().get_siblings(axes):
                if (ax in self.top_axes):
                    return ax
            return axes
        else:
            return None

    def onkey_release_debounce(self, event):
        if self.key_pressed:
            self.key_released_timer = Timer(self.press_max_seconds, self.onkey_release, [event])
            self.key_released_timer.start()

    def onkey_release(self, event):

        self.key_pressed = False
        axes = self.get_event_axes(event)

        if event.key == 'shift':
            self.shift_is_held = False

    def onkey_press(self, event):
        
        if self.key_released_timer:
            self.key_released_timer.cancel()
            self.key_released_timer = None

        self.key_pressed = True

        axes = self.get_event_axes(event)
        if axes == None:
            return

        if axes.marker_active == None:
            return
        elif event.key == 'shift':
            self.shift_is_held = True
        elif(event.key == 'left'):
            self.shift_linked(axes, -1)
            self.draw_linked(axes)
        elif(event.key == 'right'):
            self.shift_linked(axes, 1)
            self.draw_linked(axes)
        elif(event.key == 'delete'):
            self.delete_linked(axes)

    def onmotion(self, event):
        xd = event.xdata
        yd = event.ydata
        axes = self.get_event_axes(event)

        if axes == None:
            return 

        if axes != self.move or axes.marker_active == None:
            return
        
        self.move_linked(axes, xd, yd)
        self.draw_linked(axes)

    def onclick(self, event):
        axes = self.get_event_axes(event)
        self.move = axes
        if self.move == None:
            return
        m = self.get_event_marker(axes, event)
        if (m != None and axes.marker_active != m): 
            self.make_linked_active(axes, m)

    def onrelease(self, event):
        xd = event.xdata
        yd = event.ydata
        axes = self.get_event_axes(event)
        

        if (axes == None):
            return
        self.move = None

        m = self.get_event_marker(axes, event)
        active_marker = axes.marker_active

        if (m == None and (active_marker == None or self.shift_is_held == True)):
            self.add_linked(axes, xd, yd)
        elif (m != None): 
            self.make_linked_active(axes, m)
        elif (active_marker != None):
            self.move_linked(axes, xd, yd)
        else:
            return
        
        self.draw_linked(axes)
        #self.draw_all()
        return
