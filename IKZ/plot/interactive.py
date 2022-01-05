# -*- coding: utf-8 -*-
"""
@author: richter
"""

import numpy as np
from matplotlib.patches import Polygon
norm = np.linalg.norm

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
            for i in np.linspace(-w/2, w/2, 2*w-1):
                _cols = cols + vec_perp[0]*i
                _rows = rows + vec_perp[1]*i
                zi += self.data[_cols.round().astype(np.int), _rows.round().astype(np.int)]
            zi /= 2*w-1
            
            col_min = cols - vec_perp[0]*w/2
            col_max = cols + vec_perp[0]*w/2
            row_min = rows - vec_perp[1]*w/2
            row_max = rows + vec_perp[1]*w/2
            x0min, x1min = col_min[[0,-1]].round().astype(int)
            x0max, x1max = col_max[[0,-1]].round().astype(int)
            y0min, y1min = row_min[[0,-1]].round().astype(int)
            y0max, y1max = row_max[[0,-1]].round().astype(int)
        else:
            zi = self.data[cols.round().astype(np.int), rows.round().astype(np.int)]
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


