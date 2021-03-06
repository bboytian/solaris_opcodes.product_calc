# imports
import multiprocessing as mp

import matplotlib.pyplot as plt
import numpy as np
import scipy.fftpack as sfft
import scipy.interpolate as sinp
import scipy.integrate as sint
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
        tra[:, 0, :]
        for tra in np.hsplit(rayleigh_tara, rayleigh_tara.shape[1])
    ]

    # computing gcdm mask
    # gcdm_trm = np.arange(r_trm.shape[1])\
    #     < (np.argmax((SNR_tra <= NOISEALTITUDE) * r_trm, axis=1)[:, None])
    # gcdm_trm *= r_trm
    # gcdm_trm = r_trm * z_tra <= 20
    gcdm_trm = r_trm

    # working array
    CRprime_tra = NRB_tra / betamprime_tra

    # developing filter
    fig, ax = plt.subplots(ncols=2, sharey=True)

    '''
    Good profiles to observe

    20200922

    136
    269                         # very low cloud has to be handled with GCDM
    306
    375                         # double peaks
    423                         # double peak
    935                         # very sharp peak at low height, cannot see
    1030                        # noisy peak
    '''
    ts_ta = nrbdic['Timestamp']

    for j in range(a := 940, a + 1):

        # original
        sampleind = j
        print(ts_ta[j])
        # sample_ra = CRprime_tra[sampleind][gcdm_trm[sampleind]]
        # sample_ra = NRB_tra[sampleind][gcdm_trm[sampleind]]
        sample_ra = SNR_tra[sampleind][gcdm_trm[sampleind]]
        samplez_ra = z_tra[sampleind][gcdm_trm[sampleind]]


        # handling invalid values
        sample_ra[sample_ra < 0] = 0
        sample_ra = np.nan_to_num(sample_ra)

        ax[0].plot(
            sample_ra, samplez_ra,
            label='original, rejected'
        )

        # plotting moving average
        window = 51
        movavg_ra = np.convolve(sample_ra, np.ones(window), mode='same')/window
        ax[0].plot(
            movavg_ra, samplez_ra,
            label='moving average'
        )


        # low pass filter
        T = 0.015               # [km]
        fs = 1/T                # sample rate, [km^-1]
        cutoff = 5             # [km^-1]
        nyq = 0.5 * fs          # Nyquist Frequency
        order = 2
        lowpass1_ra = sample_ra
        b, a = sig.butter(order, cutoff/nyq, btype='low', analog=False)
        lowpass1_ra = sig.filtfilt(b, a, lowpass1_ra)
        p1 = ax[0].plot(lowpass1_ra, samplez_ra,
                        label='low pass')


        # savgol filter
        times = 1
        window = 51
        poly = 2
        savgol_ra = lowpass1_ra
        for time in range(times):
            savgol_ra = sig.savgol_filter(savgol_ra, window, poly)
        p2 = ax[0].plot(savgol_ra, samplez_ra,
                        label='savgol')

        # low pass filter
        T = 0.015               # [km]
        fs = 1/T                # sample rate, [km^-1]
        cutoff = 1              # [km^-1]
        nyq = 0.5 * fs          # Nyquist Frequency
        order = 2
        lowpass2_ra = savgol_ra
        b, a = sig.butter(order, cutoff/nyq, btype='low', analog=False)
        lowpass2_ra = sig.filtfilt(b, a, lowpass2_ra)
        p3 = ax[0].plot(lowpass2_ra, samplez_ra,
                        label='low pass')

        ax[0].legend()

        # first derivative
        T = 0.015
        sampledz_ra = lowpass1_ra
        sampledz_ra = np.diff(sampledz_ra) / T
        sampledzz_ra = T/2 + samplez_ra[:-1]
        sampledz_ra = sinp.interp1d(               # returns a function
            sampledzz_ra, sampledz_ra,
            kind='quadratic', fill_value='extrapolate'
        )(samplez_ra)
        ax[1].plot(
            sampledz_ra, samplez_ra, color=p1[0].get_color()
        )

        T = 0.015
        sampledz_ra = savgol_ra
        sampledz_ra = np.diff(sampledz_ra) / T
        sampledzz_ra = T/2 + samplez_ra[:-1]
        sampledz_ra = sinp.interp1d(               # returns a function
            sampledzz_ra, sampledz_ra,
            kind='quadratic', fill_value='extrapolate'
        )(samplez_ra)
        ax[1].plot(
            sampledz_ra, samplez_ra, color=p2[0].get_color()
        )

        T = 0.015
        sampledz_ra = lowpass2_ra
        sampledz_ra = np.diff(sampledz_ra) / T
        sampledzz_ra = T/2 + samplez_ra[:-1]
        sampledz_ra = sinp.interp1d(               # returns a function
            sampledzz_ra, sampledz_ra,
            kind='quadratic', fill_value='extrapolate'
        )(samplez_ra)
        ax[1].plot(
            sampledz_ra, samplez_ra, color=p3[0].get_color()
        )


        # trying gcdm thresholds
        bar = sampledz_ra
        bar = bar.mean()
        barmax = KEMPIRICAL * bar
        barmin = (1 - KEMPIRICAL) * bar

        ax[1].vlines([barmax, barmin], *ax[1].get_ylim(), color='k')



        # # inspecting frequency spectrum of savgol
        # fig, ax = plt.subplots()
        # N = len(sample_ra)
        # # sample spacing
        # T = np.diff(samplez_ra)[0]
        # xf = np.linspace(0.0, 1.0/(2.0*T), N//2)

        # yf = sfft.fft(savgol_ra)
        # ax.plot(xf, 2.0/N * np.abs(yf[:N//2]))

        # yf = sfft.fft(lowpass_ra)
        # ax.plot(xf, 2.0/N * np.abs(yf[:N//2]))

        # ax.set_yscale('log')


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

    '''
    Good profiles to observe

    20200922

    136
    269                         # very low cloud has to be handled with GCDM
    306
    375                         # double peaks
    423                         # double peak
    935                         # very sharp peak at low height, cannot see
    1030                        # noisy peak
    '''

    nrb_d = nrb_calc(
        'smmpl_E2', smmpl_reader,
        # '/home/tianli/SOLAR_EMA_project/data/smmpl_E2/20200805/202008050003.mpl',
        starttime=LOCTIMEFN('202009220000', 0),
        endtime=LOCTIMEFN('202009230000', 0),
    )

    main(nrb_d, combpolboo=True, plotboo=True)
