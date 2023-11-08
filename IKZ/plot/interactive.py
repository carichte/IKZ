# -*- coding: utf-8 -*-
"""
@author: richter
"""

import numpy as np
from matplotlib.patches import Polygon
from matplotlib.widgets import RectangleSelector
from ipywidgets import Button, VBox, HBox
from IPython.display import display

norm = np.linalg.norm
sqrt2pi = np.sqrt(2*np.pi)

stdnorm = lambda x, sigma: np.exp(-(x/sigma)**2/2)/sigma/sqrt2pi


class LineCut:
    '''Allow user to drag a line on a pcolor/pcolormesh plot, and plot the Z values from that line on a separate axis.

    Example
    -------
    fig, (ax1, ax2) = plt.subplots( nrows=2 )    # one figure, two axes
    img = ax1.pcolormesh( x, y, Z )     # pcolormesh on the 1st axis
    lntr = LineCut( img, ax2 )        # Connect the handler, plot LineCut onto 2nd axis

    Arguments
    ---------
    img: the pcolormesh plot to extract data from and that the User's clicks will be recorded for.
    ax2: the axis on which to plot the data values from the dragged line.
    integrate_width: number of pixels to average over perpendicular to the line cut


    '''
    def __init__(self, img, ax, integrate_width=1):
        '''
        img: the pcolormesh instance to get data from/that user should click on
        ax: the axis to plot the line slice on
        '''
        self.img = img
        self.ax = ax
#         self.data = img.get_array().reshape(img._meshWidth, img._meshHeight)
#         self.data = img.get_array().reshape(img._meshHeight, img._meshWidth)
        h, w, _ = img._coordinates.shape
        self.data = img.get_array().reshape(h-1, w-1)
        self.coords = img._coordinates

        # register the event handlers:
        self.cidclick = img.figure.canvas.mpl_connect('button_press_event', self)
        self.cidrelease = img.figure.canvas.mpl_connect('button_release_event', self)

        self.markers, self.arrow = None, None   # the lineslice indicators on the pcolormesh plot
        self.line = None    # the lineslice values plotted in a line
        self.box = None
        self.linecut = None
        self.integrate_width = integrate_width

        
    def __call__(self, event):
        '''Matplotlib will run this function whenever the user triggers an event on our figure'''
        if event.inaxes != self.img.axes:
            return     # exit if clicks weren't within the `img` axes
        if bool(self.ax.figure.canvas.manager.toolbar.mode):
            return   # exit if pyplot toolbar (zooming etc.) is active
#         if self.img.figure.canvas.manager.toolbar._active is not None:
#             return   # exit if pyplot toolbar (zooming etc.) is active

        if event.name == 'button_press_event':
            self.p1 =  (event.xdata, event.ydata)    # save 1st point
        elif event.name == 'button_release_event':
            self.p2 = (event.xdata, event.ydata)    # save 2nd point
            self.drawLineCut()    # draw the Line Slice position & data

    def drawLineCut( self ):
        ''' Draw the region along which the Line Slice will be extracted, onto the original self.img pcolormesh plot.  Also update the self.axis plot to show the line slice data.'''
        '''Uses code from these hints:
        http://stackoverflow.com/questions/7878398/how-to-extract-an-arbitrary-line-of-values-from-a-numpy-array
        http://stackoverflow.com/questions/34840366/matplotlib-pcolor-get-array-returns-flattened-array-how-to-get-2d-data-ba
        '''

        x0,y0 = self.p1[0], self.p1[1]  # get user's selected coordinates
        x1,y1 = self.p2[0], self.p2[1]
        
        
        i1, j1 = np.unravel_index(norm(self.coords - self.p1, axis=2).argmin(), self.coords.shape[:2])
        i2, j2 = np.unravel_index(norm(self.coords - self.p2, axis=2).argmin(), self.coords.shape[:2])
        
        
        length = int(np.hypot(i2-i1, j2-j1))
        cols, rows = np.linspace(i1, i2, length),   np.linspace(j1, j2, length)
        x = np.linspace(x0, x1, length)
        y = np.linspace(y0, y1, length)
        
        if abs(x0-x1) > abs(y0-y1):
            xplot = x
            xlabel = self.img.axes.get_xlabel()
        else:
            xplot = y
            xlabel = self.img.axes.get_ylabel()

        # Extract the values along the line with nearest-neighbor pixel value:
        # get temp. data from the pcolor plot
        if self.integrate_width > 1:
            zi = np.zeros(len(cols))
            # vec_par  = np.array((i2-i1, j2-j1), dtype=float)
            self.ij = i1, j1 = int(i1), int(j1)
            self.Qtrafo = (self.coords[[i1+1,i1],[j1,j1+1]] - self.coords[i1,j1]).T
            Qtrafo_inv = np.linalg.inv(self.Qtrafo)
            
            vec_par  = np.array((x1-x0, y1-y0), dtype=float)
            vec_perp = np.array([[0,-1], [1,0]]).dot(vec_par)
            vec_perp = Qtrafo_inv.dot(vec_perp)
            vec_perp /=np.linalg.norm(vec_perp)

            w = self.integrate_width
            for i in np.linspace(-3*w, 3*w, 6*w+1):
                _cols = cols + vec_perp[0]*i
                _rows = rows + vec_perp[1]*i
                zi += self.data[_cols.round().astype(int)-1, _rows.round().astype(int)-1] * stdnorm(i, w)
            
            col_min = cols - vec_perp[0]*w*2
            col_max = cols + vec_perp[0]*w*2
            row_min = rows - vec_perp[1]*w*2
            row_max = rows + vec_perp[1]*w*2
            x0min, x1min = col_min[[0,-1]].round().astype(int)
            x0max, x1max = col_max[[0,-1]].round().astype(int)
            y0min, y1min = row_min[[0,-1]].round().astype(int)
            y0max, y1max = row_max[[0,-1]].round().astype(int)
        else:
            zi = self.data[cols.round().astype(int), rows.round().astype(int)]
        # Extract the values along the line, using cubic interpolation:
        #import scipy.ndimage
        #zi = scipy.ndimage.map_coordinates(self.data, np.vstack((x,y)))
        
        self.linecut = np.array((x, y, zi)).T # this allows to access the result

        # if plots exist, delete them:
        if self.markers != None:
            if isinstance(self.markers, list):
                self.markers[0].remove()
            else:
                self.markers.remove()
        if self.arrow != None:
            self.arrow.remove()

        # plot the endpoints
        self.markers = self.img.axes.plot([x0, x1], [y0, y1], 'wo')   
        # plot an arrow:
        self.arrow = self.img.axes.annotate("",
                    xy=(x0, y0),    # start point
                    xycoords='data',
                    xytext=(x1, y1),    # end point
                    textcoords='data',
                    arrowprops=dict(
                        arrowstyle="<-",
                        connectionstyle="arc3", 
                        color='white',
                        alpha=0.5,
                        linewidth=1
                        ),

                    )
        if self.integrate_width > 1:
            if self.box is not None:
                self.box.remove()
            self.boxcoords = [self.coords[x0min, y0min],
                   self.coords[x0max, y0max],
                   self.coords[x1max, y1max],
                   self.coords[x1min, y1min],
                   ]
            self.box = Polygon(self.boxcoords, color="w", edgecolor=None, alpha=0.25)
            self.img.axes.add_patch(self.box)
        # plot the data along the line on provided `ax`:
        if self.line != None:
            self.line[0].remove()   # delete the plot
        self.line = self.ax.plot(xplot, zi)
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel(xlabel)


class ROIselector(object):
    """
        A ROI-selector for Jupyter Notebooks:
        
        ```
            fig, ax = plt.subplots(1, 1)
            ax.imshow(myimage)
            RS = ROIselector(ax)
            print(RS.rois)
        ```
    """
    def __init__(self, axes, maxrois=10, roicolor="orange"):
        self.ax = axes
        self.maxrois = 10
        self.rois = dict()
        self._roiplots = dict()
        self.roicolor = roicolor

        self.addbutton = Button(description='Add Region')
        self.addbutton.on_click(self.addroi)
        self.undobutton = Button(description='Clear Last Region')
        self.undobutton.on_click(self.clear_last_rois)
        self.clrbutton = Button(description='Clear Regions')
        self.clrbutton.on_click(self.clear_rois)

        self.rect = RectangleSelector(self.ax, lambda : None,
                                      drawtype='box', useblit=True,
                                      button=[1, 3],  # don't use middle button
                                      minspanx=5, minspany=5,
                                      spancoords='pixels',
                                      interactive=True)
        self.buttons = self.addbutton, self.undobutton, self.clrbutton
        display(HBox(self.buttons))

    def addroi(self, button):
        iroi = len(self.rois)+1
        rname = "roi_%02i"%iroi
        'eclick and erelease are the press and release events'
        x1, x2, y1, y2 = list(map(int, self.rect.extents))
        print("(%i, %i) --> (%i, %i)" % (x1, y1, x2, y2))
        self.rois[rname] = np.s_[y1:y2, x1:x2]
        box_x = [x1, x2, x2, x1, x1]
        box_y = [y1, y1, y2, y2, y1]
        imark,jmark = min(box_x), max(box_y)
        c = self.roicolor
        line, = self.ax.plot(box_x, box_y, "-", ms=1, color=c, alpha=0.71)
        lbl = self.ax.annotate(rname, (imark, jmark), color=c)
        self._roiplots[rname] = (line, lbl)

    def clear_last_rois(self, button):
        iroi = len(self.rois)
        if not iroi>0:
            return
        rname = "roi_%02i"%iroi
        self.rois.pop(rname)
        line, lbl = self._roiplots.pop(rname)
        self.ax.lines.remove(line)
        self.ax.texts.remove(lbl)
        self.ax.figure.canvas.draw()

    def clear_rois(self, button):
        self.rois.clear()
        for rname in self._roiplots:
            line, lbl = self._roiplots[rname]
            self.ax.lines.remove(line)
            self.ax.texts.remove(lbl)
        self._roiplots.clear()
        self.ax.figure.canvas.draw()
        
        



