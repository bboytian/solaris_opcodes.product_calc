# imports
import multiprocessing as mp

import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as sig

from .gcdm_algo import main as gcdm_algo
from .gradient_calc import main as gradient_calc
from ...constant_profiles import rayleigh_gen
from ....global_imports.solaris_opcodes import *


# main func
@verbose
@announcer
def main(
        nrbdic,
        combpolboo=True,
        plotboo=False,
):
    '''
    Gradient-based Cloud Detection (GCDM) according to Lewis et. al 2016.
    Overview of MPLNET Version 3 Cloud Detection
    Calculates cloud product up till defined SNR threshold; NOISEALTITUDE
    Scattering profile is kept in .constant_profiles

    Future
        - KEMPIRICAL might be passed in as an argument for optimization/quality
          check in the future

    Parameters
        nrbdic (dict): output from .nrb_calc.py
        combpolboo (boolean): gcdm on combined polarizations or just co pol
        plotboo (boolean): whether or not to plot computed results
    '''
    # reading data
    if combpolboo:
        NRB_tra = nrbdic['NRB_tra']
        SNR_tra = nrbdic['SNR_tra']
    else:
        NRB_tra = nrbdic['NRB2_tra']  # co-pol
        SNR_tra = nrbdic['SNR2_tra']
    r_trm = nrbdic['r_trm']

    # retrieving scattering profile
    try:                        # scanning lidar NRB
        setz_a = nrbdic['DeltNbinpadtheta_a']
        setzind_ta = nrbdic['DeltNbinpadthetaind_ta']
        z_tra = nrbdic['z_tra']
    except KeyError:            # vertical lidar NRB
        setz_a = nrbdic['DeltNbinpad_a']
        setzind_ta = nrbdic['DeltNbinpadind_ta']
        z_tra = nrbdic['r_tra']

    # retreiving molecular profile
    rayleigh_aara = np.array([
        rayleigh_gen(*setz) for setz in setz_a
    ])
    rayleigh_tara = np.array([
        rayleigh_aara[setzind] for setzind in setzind_ta
    ])
    _, _, betamprime_tra, _ = [
        tra[0]
        for tra in np.hsplit(rayleigh_tara, rayleigh_tara.shape[1])
    ]

    # computing gcdm mask
    # gcdm_trm = np.arange(r_trm.shape[1])\
    #     < (np.argmax((SNR_tra <= NOISEALTITUDE) * r_trm, axis=1)[:, None])
    # gcdm_trm *= r_trm
    gcdm_trm = r_trm * z_tra <= 20

    # working array
    CRprime_tra = NRB_tra / betamprime_tra

    # developing filter
    fig, axs = plt.subplots(ncols=5, sharey=True)

    for j in range(a := 25, a + 2):

        # original
        sampleind = j
        sample_ra = CRprime_tra[sampleind][gcdm_trm[sampleind]]
        samplez_ra = z_tra[sampleind][gcdm_trm[sampleind]]

        # # removing invalid points
        # boo_ra = sample_ra > 0
        # sample_ra = sample_ra[boo_ra]
        # samplez_ra = samplez_ra[boo_ra]

        sample_ra[sample_ra<0] = 0
        sample_ra = np.nan_to_num(sample_ra)

        # axs[0].plot(
        #     sample_ra, samplez_ra,
        #     # label='original, rejected'
        # )


        # observing noise frequencies
        ## fourier transform
        N = len(sample_ra)
        # sample spacing
        T = np.diff(samplez_ra)[0]
        xf = np.linspace(0.0, 1.0/(2.0*T), N//2)
        import scipy.fftpack as spf
        yf = spf.fft(sample_ra)
        # plt.plot(xf, 2.0/N * np.abs(yf[:N//2]))

        y = spf.ifft(yf)
        plt.plot(samplez_ra, np.abs(y))

        cutoff = 30
        matchxf = np.concatenate([xf, [cutoff], xf[::-1]])
        yf[matchxf>=cutoff] = 0

        y = spf.ifft(yf)
        plt.plot(samplez_ra, np.abs(y))

        plt.yscale('log')
        plt.show()



        # savgol_filter
        times = 1
        window = 51
        poly = 2
        savgol_ra = sample_ra
        for time in range(times):
            savgol_ra = sig.savgol_filter(savgol_ra, window, poly)
        p = axs[1].plot(savgol_ra, samplez_ra,
                        label='savgol')

        # lowpass filter



    # for ax in axs:
    #     ax.set_xscale('log')
    plt.show()






    # # computing first derivative
    # dzCRprime_tra = gradient_calc(CRprime_tra, z_tra, setz_a, setzind_ta)

    # # Computing threshold
    # CRprime0_tra = np.copy(CRprime_tra).flatten()
    # CRprime0_tra[~(gcdm_trm.flatten())] = np.nan  # set nan to ignore in average
    # CRprime0_tra = CRprime0_tra.reshape(*(gcdm_trm.shape))
    # barCRprime0_ta = np.nanmean(CRprime0_tra, axis=1)
    # amax_ta = KEMPIRICAL * barCRprime0_ta
    # amin_ta = (1 - KEMPIRICAL) * barCRprime0_ta


if __name__ == '__main__':
    from ...nrb_calc import main as nrb_calc
    from ....file_readwrite import smmpl_reader

    nrb_d = nrb_calc(
        'smmpl_E2', smmpl_reader,
        '/home/tianli/SOLAR_EMA_project/data/smmpl_E2/20200805/202008050003.mpl',
        # starttime=LOCTIMEFN('202009010000', UTCINFO),
        # endtime=LOCTIMEFN('202009010800', UTCINFO),
        genboo=True,
    )

    main(nrb_d, combpolboo=True, plotboo=True)