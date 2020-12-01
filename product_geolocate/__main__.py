# imports
import numpy as np
from pymap3d import ned2geodetic

from .intelligent_averaging import main as intelligent_averaging
from .nearestneighbour_average import main as nearestneighbour_average
from ...global_imports.solaris_opcodes import *


# main func
def main(
        pixelsize, gridlen,
        latitude, longitude, elevation,

        product_d,
        producttype_l,

        peakonly_boo,
):
    '''
    geolocates the products provided to a map like grid. It augments the data in
    product_d with the geolocated data.
    the product mask has to be of shape
    (time, no. of layers, 3(mask bottom, mask peak , mask top))

    Parameters
        pixelsize (float): [km] pixel size for data sampling
        gridlen (int): length of map grid in consideration for geolocation
        latitude (float): [deg] coords of lidar
        longitude (float): [deg] coords of lidar
        elevation (float): [m] height of lidar from MSL

        product_d (dict): dictionary containing all relevant information
        producttype_l (list): list of keys of the product types which we would to
                              perform pixel averaging and geolocation

        peakonly_boo (boolean): decides whether or not to return the
                                average for each layer or just the
                                layer with the most number of points

    Return
        product_d (dict): with the following keys added
            LATITUDEKEY: (np.ndarray): latitude coordinates of pixel
            LONGITUDEKEY: (np.ndarray): longitude coordinates of pixel

    '''
    # reading product and relevant arrays
    array_d = product_d[NRBKEY]
    theta_ta = array_d['theta_ta']
    phi_ta = array_d['phi_ta']

    # centering on provided coordinates; finding center NED of pixels
    # we ignore elevation effects when translating between pixels
    centern, centere = 0, 0

    ## finding coordinate limits; [[left_lim, center, right_lim], ...]
    ## shape (gridlen, gridlen, 2(north, east), 3(left_lim, center, right_lim))
    if gridlen%2:
        gridrange = np.arange(
            -(gridlen//2)*pixelsize, (gridlen//2 + 1)*pixelsize, pixelsize
        )
    else:
        gridrange = np.arange(
            -(gridlen/2 - 0.5)*pixelsize, (gridlen/2 + 0.5)*pixelsize, pixelsize
        )
    coordlim_gg2a = np.stack(np.meshgrid(gridrange, gridrange), axis=-1)
    coordlim_gg23a = np.stack(
        [
            coordlim_gg2a - pixelsize/2,
            coordlim_gg2a,
            coordlim_gg2a + pixelsize/2
        ], axis=-1
    )

    for key in producttype_l:
        prodmask_tl3a = product_d[key][MASKKEY]

        # convert product to cartesian grid coordinates
        # (time*max no. of layers., 3(mask bottom, mask peak, mask top))
        xprodmask_tl3a = prodmask_tl3a \
            * np.tan(theta_ta)[:, None, None] * np.cos(phi_ta)[:, None, None]
        yprodmask_tl3a = prodmask_tl3a \
            * np.tan(theta_ta)[:, None, None] * np.sin(phi_ta)[:, None, None]

        ## flattening and removing all completemly invalid layers
        prodmask_a3a = prodmask_tl3a.reshape((-1, 3))
        xprodmask_a3a = xprodmask_tl3a.reshape((-1, 3))
        yprodmask_a3a = yprodmask_tl3a.reshape((-1, 3))

        invalidlayer_am = ~(np.isnan(xprodmask_a3a).all(axis=-1))
        prodmask_a3a = prodmask_a3a[invalidlayer_am]
        xprodmask_a3a = xprodmask_a3a[invalidlayer_am]
        yprodmask_a3a = yprodmask_a3a[invalidlayer_am]
        xyprodmask_a23a = np.stack([xprodmask_a3a, yprodmask_a3a], axis=1)

        # locating product into it's respective pixel
        ## using an array of masks of shape a3a, each element in the array is a pixel
        prodmask_gga23m = \
            (
                coordlim_gg23a[:, :, None, :, [0]]
                <= xyprodmask_a23a[None, None, :, :]
            )\
            * (
                coordlim_gg23a[:, :, None, :, [2]]
                >= xyprodmask_a23a[None, None, :, :]
            )
        prodmask_gga3m = prodmask_gga23m.prod(axis=3).astype(np.bool)

        ## boolean slicing arrays, one array for mask bottom, peak, and top
        prodbot_ggam = prodmask_gga3m[..., 0]
        prodpeak_ggam = prodmask_gga3m[..., 1]
        prodtop_ggam = prodmask_gga3m[..., 2]
        ### initialising empty grid
        prodbot_ggAl = [[None]*gridlen]*gridlen
        prodpeak_ggAl = [[None]*gridlen]*gridlen
        prodtop_ggAl = [[None]*gridlen]*gridlen
        ### captical 'A' here represents variable length arrays in the list
        for i in range(gridlen):
            for j in range(gridlen):

                # placing product masks into their respective pixels
                prodbot_ggAl[i][j] = prodmask_a3a[:, 0][prodbot_ggam[i][j]]
                prodpeak_ggAl[i][j] = prodmask_a3a[:, 0][prodpeak_ggam[i][j]]
                prodtop_ggAl[i][j] = prodmask_a3a[:, 0][prodtop_ggam[i][j]]


        # averaging within the pixel
        # averaging of layers within each pixel is sorted by their altitudes
                prodbot_ggAl[i][j] = intelligent_averaging(prodbot_ggAl[i][j],
                                                           peakonly_boo)
                prodpeak_ggAl[i][j] = intelligent_averaging(prodpeak_ggAl[i][j],
                                                            peakonly_boo)
                prodtop_ggAl[i][j] = intelligent_averaging(prodtop_ggAl[i][j],
                                                           peakonly_boo)

        # interpolating across pixels if there is an empty pixel
        # for a given empty pixel, we shall take the average of lowest layer
        # from the neighbouring pixels
        prodbot_ggAl = nearestneighbour_average(prodbot_ggAl)
        prodpeak_ggAl = nearestneighbour_average(prodpeak_ggAl)
        prodtop_ggAl = nearestneighbour_average(prodtop_ggAl)

        # correcting product height for elevation of lidar

        # reshaping and adding to the dictionary

    return product_d
