# imports
import os.path as osp

import netCDF4 as nc
import numpy as np
from scipy.integrate import cumtrapz

from ....global_imports.solaris_opcodes import *


# static params
_mollidrat = np.pi*8/3   # molecular lidar ratio


# main func
@verbose
@announcer
def main(
        Delt, Nbin, pad, theta=0,
        weather=WEATHER, wavelength=WAVELENGTH
):
    '''
    function that reads rayleigh-523_sing.cdf, stores data for the stated lambda

    Future
        - The rayleigh profile and it's uncertainties could be derived from aeronet

    Parameters
        Delt (float): bintime
        Nbin (int): number of bins
        pad (int): padding of '0's to place at the front of the array to
                   rectangularise the final output
        (optional) theta (float): [rad] lidar to zenith angle
        wavelength (float): [nm], wavelength of light used
        weather (str): 'winter' or 'summer'

    Return
        betam_ra (np.array): molecular backscattering w.r.t altitude
        T2m_ra (np.array): molecular transmission squared w.r.t altitude
        betamprime_ra (np.array): attenuated molecular back scattering w.r.t
                                  altitude
        delfbetamprimes_ra (np.array): fractional uncertainty of att backscatter
                                       squared
    '''
    # reading scattering coefficient file
    ray_file = DIRCONFN(osp.dirname(osp.abspath(__file__)),
                        RAYLEIGHCDFDIR.format(RAYLEIGHCDLAMBDA))
    print(f'using profile from :{ray_file}')
    print(f'\tDelt: {Delt}')
    print(f'\tNbin: {Nbin}')
    print(f'\tpad: {pad}')
    print(f'\ttheta: {theta}')

    rayscatdat_nc = nc.Dataset(ray_file, 'r', format='NETNC4_CLASSIC')
    ncr_ra = rayscatdat_nc.variables['range'][:]
    betam_ra = rayscatdat_nc.variables[weather+'_ray'][:]

    # interpolating
    Nbin = int(Nbin)
    pad = int(pad)
    Delr = SPEEDOFLIGHT * Delt
    z_ra = np.append(np.zeros(pad), Delr * np.arange(Nbin))
    betam_ra = np.interp(z_ra, ncr_ra, betam_ra)

    # computing back scatter
    betam_ra *= ((wavelength/RAYLEIGHCDLAMBDA)**(-4))

    # computing transmission
    sigmam_ra = _mollidrat * betam_ra              # scat cross sec
    Tm2_ra = np.exp(-2 * cumtrapz(sigmam_ra, z_ra, initial=0))

    # computing product
    betamprime_ra = betam_ra * Tm2_ra

    # computing uncertainties
    delfbetamprimes_ra = (RAYLEIGHATTUNCERT**2) * np.ones_like(betam_ra)

    # returning
    ret_l = [
        betam_ra, Tm2_ra, betamprime_ra,
        delfbetamprimes_ra
    ]
    return ret_l


# generating
if __name__ == '__main__':
    import matplotlib.pyplot as plt

    Delt = 2.5e-7
    Nbin = 798
    Delr = Delt * SPEEDOFLIGHT
    r_ra = Delr * np.arange(Nbin)
    betam_ra, Tm2_ra, betamprime_ra, delbetamprime_ra = main(Delt, Nbin, 0)

    plt.plot(betamprime_ra, r_ra, 'bx')
    plt.plot(betam_ra, r_ra)
    # plt.plot(Tm2_ra, r_ra, 'ro')
    # plt.ylim([0, 20])
    plt.show()
