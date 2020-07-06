import os

import numpy as np
import deepdish

from .harmonics import sYlm


# Constants for conversions
CC = 299792458.0  # speed of light in m/s
GG = 6.67384e-11  # Newton in m^3 / (KG s^2)
SOLAR_MASS = 1.98855 * 10 ** (30)  # solar mass in  KG
KG = 1 / SOLAR_MASS
METRE = CC ** 2 / (GG * SOLAR_MASS)
SECOND = CC * METRE

MPC = 3.08568e22  # MPC in metres


def m12_to_mc(m1, m2):
    """convert m1 and m2 to chirp mass"""
    return (m1 * m2) ** (3.0 / 5.0) / (m1 + m2) ** (1.0 / 5.0)


def m12_to_symratio(m1, m2):
    """convert m1 and m2 to symmetric mass ratio"""
    return m1 * m2 / (m1 + m2) ** 2


def mc_eta_to_m12(mc, eta):
    """
    Convert chirp mass and symmetric mass ratio to component masses.

    Input: mc - chirp mass
    eta - symmetric mass ratio
    Return: m1, m2 - primary and secondary masses, m1>m2
    """
    m1 = mc / eta ** 0.6 * (1 + (1 - 4 * eta) ** 0.5) / 2
    m2 = mc / eta ** 0.6 * (1 - (1 - 4 * eta) ** 0.5) / 2
    return m1, m2


def m_sol_to_geo(mm):
    """convert from solar masses to geometric units"""
    return mm / KG * GG / CC ** 2


def m_geo_to_sol(mm):
    """convert from geometric units to solar masses"""
    return mm * KG / GG * CC ** 2


def time_s_to_geo(time):
    """convert time from seconds to geometric units"""
    return time * CC


def time_geo_to_s(time):
    """convert time from seconds to geometric units"""
    return time / CC


def freq_Hz_to_geo(freq):
    """convert freq from Hz to geometric units"""
    return freq / CC


def freq_geo_to_Hz(freq):
    """convert freq from geometric units to Hz"""
    return freq * CC


def dist_Mpc_to_geo(dist):
    """convert distance from MPC to geometric units (i.e., metres)"""
    return dist * MPC


def nfft(ht, sampling_frequency):
    """
    performs an FFT while keeping track of the frequency bins
    assumes input time series is real (positive frequencies only)

    ht = time series
    sampling_frequency = sampling frequency

    returns
    hf = single-sided FFT of ft normalised to units of strain / sqrt(Hz)
    f = frequencies associated with hf
    """
    # add one zero padding if time series does not have even number
    # of sampling times
    if np.mod(len(ht), 2) == 1:
        ht = np.append(ht, 0)
    LL = len(ht)
    # frequency range
    ff = sampling_frequency / 2 * np.linspace(0, 1, int(LL / 2 + 1))

    # calculate FFT
    # rfft computes the fft for real inputs
    hf = np.fft.rfft(ht)

    # normalise to units of strain / sqrt(Hz)
    hf = hf / sampling_frequency

    return hf, ff


def load_sxs_waveform(file_name, modes=None, extraction="OutermostExtraction.dir"):
    """
    Load the spherical harmonic modes of an SXS numerical relativity waveform.

    Parameters
    ----------
    file_name: str
        Name of file to be loaded.
    modes: dict
        Dictionary of spherical harmonic modes to extract,
        default is all in ell<=4.
    extraction: str
        String representing extraction method, default is
        'OutermostExtraction.dir'
    Returns
    -------
    output: dict
        Dictionary of requested spherical harmonic modes.
    """
    waveform = deepdish.io.load(file_name)
    output = dict()
    if modes is None:
        for ell in range(2, 5):
            for mm in range(-ell, ell + 1):
                mode_array = waveform[extraction][
                    "Y_l{}_m{}.dat".format(ell, mm)[:, 1:]
                ]
                output[(ell, mm)] = mode_array[:, 1] + 1j * mode_array[:, 2]
    else:
        for mode in modes:
            mode_array = waveform[extraction]["Y_l{}_m{}.dat".format(mode[0], mode[1])]
            output[mode] = mode_array[:, 1] + 1j * mode_array[:, 2]
    times = mode_array[:, 0]
    return output, times


def combine_modes(h_lm, inc, phase):
    """
    Calculate the plus and cross polarisations of the waveform from the
    spherical harmonic decomposition.
    """
    total = sum([h_lm[(l, m)] * sYlm(-2, l, m, inc, phase) for l, m in h_lm])
    h_plus_cross = dict(plus=total.real, cross=-total.imag)
    return h_plus_cross


def get_version_information():
    version_file = os.path.join(os.path.dirname(__file__), ".version")
    try:
        with open(version_file, "r") as f:
            return f.readline().rstrip()
    except EnvironmentError:
        print("No version information file '.version' found")


def planck(M, e, sym=True):
    r"""Return a Planck-taper window.
    The Planck-taper is a window which is smooth and differentiable everywhere.
    It's designed to minimize leakage outside of a frequency of interest
    without supressing signals which might contain the most power at the edges
    of the waveform.
    Taken from https://github.com/scipy/scipy/pull/6012/files
    Parameters
    ----------
    M : int
        Number of points in the output window. If zero or less, an empty
        array is returned. The Planck-taper is defined for 3 points onward
        (with M<3 returning a boxcar window instead).
    e : float
        Epsilon parameter (0<e<0.5). Values of e>=0.5 result in no flat region.
    sym : bool, optional
        When True (default), generates a symmetric window, for use in filter
        design.
        When False, generates a periodic window, for use in spectral analysis.
    Returns
    -------
    w : ndarray
        The window, with the maximum value normalized to 1 (though the value 1
        does not appear for e>=0.5 if `M` is even and `sym` is True).
    References
    ----------
    .. [1] DJA McKechan, C Robinson and BS Sathyaprakash, (2010) A tapering
           window for time-domain templates and simulated signals in the
           detection of gravitational waves from coalescing compact binaries;
           Classical and Quantum Gravity 27 (8): 084020. arXiv:1003.2939.
    Examples
    --------
    Plot the window and its frequency response:
    >>> from scipy import signal
    >>> from scipy.fftpack import fft, fftshift
    >>> import matplotlib.pyplot as plt
    >>> window = signal.planck(51, 0.1)
    >>> plt.plot(window)
    >>> plt.title("Planck-taper window ($\epsilon = 0.1$)")
    >>> plt.ylabel("Amplitude")
    >>> plt.xlabel("Sample")
    >>> plt.figure()
    >>> A = fft(window, 2048) / (len(window)/2.0)
    >>> freq = np.linspace(-0.5, 0.5, len(A))
    >>> response = 20 * np.log10(np.abs(fftshift(A / abs(A).max())))
    >>> plt.plot(freq, response)
    >>> plt.axis([-0.5, 0.5, -120, 0])
    >>> plt.title("Frequency response of the Planck-taper window ($\epsilon = 0.1$)")
    >>> plt.ylabel("Normalized magnitude [dB]")
    >>> plt.xlabel("Normalized frequency [cycles per sample]")
    """
    if M < 1:
        return np.array([])
    if M < 3:
        return np.ones(M, "d")
    odd = M % 2
    if not sym and not odd:
        M = M + 1

    t2 = min(M // 2, int(np.floor(e * (M - 1))))
    w1 = np.arange(1, t2)
    w1 = t2 / w1 + t2 / (w1 - t2)
    w1 = 1 / (np.exp(w1) + 1)
    w2 = np.ones(M - 2 - len(w1) * 2)
    w3 = w1[::-1]
    w = np.concatenate(([0.0], w1, w2, w3, [0.0]))

    if not sym and not odd:
        w = w[:-1]
    return w
