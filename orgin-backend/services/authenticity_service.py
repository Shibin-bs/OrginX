"""
OriginX — Advanced Forensic Authenticity Engine v3
====================================================
10-signal multi-domain forensic analysis with nonlinear decision fusion,
co-occurrence amplification, and hard-override rejection rules.

Designed to detect state-of-the-art diffusion (Stable Diffusion, DALL-E,
Midjourney), GAN, and composite/spliced images while minimising false
positives on natural smartphone and DSLR photographs.

Signals
-------
 1. ELA  — Error Level Analysis (compression inconsistency)
 2. MSR  — Multi-Scale Residual variance-decay modelling
 3. RAC  — Residual Autocorrelation (structured noise persistence)
 4. WBE  — Wavelet Band Energy & cross-band correlation
 5. FFT  — Frequency-domain spectral slope & band ratios
 6. LPS  — Local Patch Statistics (entropy + variance diversity)
 7. GEC  — Gradient & Edge Coherence (kurtosis, phase congruency)
 8. RCD  — RGB Channel Residual Divergence (correlation + KL)
 9. PLO  — Pixel-Level Outlier Analysis (neighbourhood consistency)
10. BCC  — Background Consistency Check (fg/bg texture contrast)

Decision pipeline
-----------------
 ① Weighted base score
 ② Co-occurrence count (signals > 0.60)
 ③ Sigmoid amplification when count ≥ 2
 ④ Hard-override reject rules
 ⑤ Threshold = 0.50

Dependencies: NumPy, OpenCV, SciPy, PyWavelets, Pillow
CPU-only. No external APIs. No pretrained models.
"""

import io
import math
import numpy as np
import cv2
from PIL import Image
from scipy import stats as sp_stats
from scipy.ndimage import uniform_filter

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False


# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

WEIGHTS = {
    "ela":       0.08,
    "msr":       0.14,
    "rac":       0.10,
    "wbe":       0.13,
    "fft":       0.12,
    "lps":       0.10,
    "gec":       0.10,
    "rcd":       0.10,
    "plo":       0.06,
    "bcc":       0.07,
}

RISK_THRESHOLD     = 0.99
CO_OCC_THRESHOLD   = 0.65   # per-signal anomaly threshold
SIGMOID_BOOST      = 0.35   # amplification factor per co-occurring signal
MAX_DIMENSION      = 1024
MIN_DIMENSION      = 32
ELA_QUALITY        = 75
BLUR_KERNELS       = [3, 5, 9, 15]
PATCH_SIZE         = 32

# Human-readable labels for each signal
SIGNAL_LABELS = {
    "ela_score":                     "compression residual inconsistency (ELA)",
    "multi_scale_residual_score":    "unnatural multi-scale noise decay",
    "residual_autocorrelation_score":"structured noise persistence (autocorrelation)",
    "wavelet_band_energy_score":     "anomalous wavelet sub-band energy symmetry",
    "fft_spectral_score":            "frequency spectrum deviates from natural 1/f law",
    "local_patch_stats_score":       "reduced local texture / entropy diversity",
    "gradient_edge_score":           "abnormal gradient distribution (edge coherence)",
    "rgb_channel_divergence_score":  "low cross-channel noise divergence (synthetic fingerprint)",
    "pixel_outlier_score":           "pixel neighbourhood consistency anomaly",
    "background_consistency_score":  "overly uniform background texture",
}


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _load_and_prepare(image_bytes: bytes):
    """Decode, validate, resize, return (BGR, PIL_RGB, gray_f64)."""
    try:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        raise ValueError(f"Cannot decode image: {e}")

    w, h = pil_img.size
    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        raise ValueError(f"Image too small ({w}x{h}).")

    if max(w, h) > MAX_DIMENSION:
        s = MAX_DIMENSION / max(w, h)
        pil_img = pil_img.resize((int(w * s), int(h * s)), Image.LANCZOS)

    rgb = np.array(pil_img, dtype=np.uint8)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float64)
    return bgr, pil_img, gray


def _c(v, lo=0.0, hi=1.0):
    """Clamp to [lo, hi]."""
    return float(max(lo, min(hi, v)))


def _sd(a, b, d=0.0):
    """Safe division."""
    return a / b if abs(b) > 1e-12 else d


def _sigmoid(x):
    """Logistic sigmoid, numerically stable."""
    x = float(x)
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)


def _hist_entropy(data, bins=256, rng=None):
    """Shannon entropy of histogram of data."""
    hist, _ = np.histogram(data, bins=bins, range=rng)
    hist = hist[hist > 0].astype(np.float64)
    t = hist.sum()
    if t == 0:
        return 0.0
    p = hist / t
    return float(-np.sum(p * np.log2(p)))


# ═══════════════════════════════════════════════════════════
# SIGNAL 1 — ERROR LEVEL ANALYSIS (ELA)
# ═══════════════════════════════════════════════════════════

def _s01_ela(pil_img):
    """
    ELA: Re-compress to JPEG Q75, compute |orig − recomp|.
    μ (mean) and CV (coefficient of variation = σ/μ) of the
    difference indicate compression-history consistency.
    
    Natural single-source JPEGs: μ ≈ 2–8, CV ≈ 1.5–3.0
    Synthetic (never compressed): μ < 1, CV < 1.0
    Composited / spliced: locally elevated μ
    """
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=ELA_QUALITY)
    buf.seek(0)
    recomp = np.array(Image.open(buf).convert("RGB"), dtype=np.float64)
    orig = np.array(pil_img, dtype=np.float64)
    diff = np.abs(orig - recomp)

    mu = float(np.mean(diff))
    sigma = float(np.std(diff))
    cv = _sd(sigma, mu)

    # Scoring —
    s = 0.0
    # Mean component
    if mu < 1.0:
        s += 0.40 + (1.0 - mu) * 0.35
    elif mu > 12.0:
        s += 0.25 + min((mu - 12.0) * 0.02, 0.30)
    else:
        s += mu * 0.012
    # CV component
    if cv < 1.0:
        s += 0.25 + (1.0 - cv) * 0.20
    elif cv > 4.0:
        s += 0.10
    else:
        s += 0.04

    return _c(s), {"ela_mu": round(mu, 3), "ela_cv": round(cv, 3)}


# ═══════════════════════════════════════════════════════════
# SIGNAL 2 — MULTI-SCALE RESIDUAL (MSR)
# ═══════════════════════════════════════════════════════════

def _s02_msr(gray):
    """
    At each Gaussian kernel k ∈ {3,5,9,15}:
      residual_k = gray − GaussianBlur(gray, k)
      var_k = Var(residual_k)

    Natural images: log(var) decays linearly with log(k),
    slope ≈ −1.5 to −3.5, R² > 0.90.
    Synthetic: flat decay (slope near 0) or poor R².
    """
    variances = []
    entropies = []
    for k in BLUR_KERNELS:
        blurred = cv2.GaussianBlur(gray, (k, k), 0)
        res = gray - blurred
        variances.append(max(float(np.var(res)), 1e-12))
        entropies.append(_hist_entropy(res, bins=256, rng=(-128, 128)))

    log_k = np.log(np.array(BLUR_KERNELS, dtype=np.float64))
    log_v = np.log(np.array(variances))
    slope, _, r_val, _, _ = sp_stats.linregress(log_k, log_v)
    r_sq = r_val ** 2
    abs_s = abs(slope)
    mean_ent = float(np.mean(entropies))

    # Slope scoring
    if abs_s < 0.8:
        ss = 0.65 + (0.8 - abs_s) * 0.40
    elif abs_s > 5.0:
        ss = 0.45 + min((abs_s - 5.0) * 0.05, 0.30)
    elif 1.5 <= abs_s <= 3.5:
        ss = 0.08
    else:
        ss = 0.25
    # Fit scoring
    if r_sq < 0.70:
        fs = 0.50 + (0.70 - r_sq) * 0.55
    elif r_sq < 0.90:
        fs = 0.15 + (0.90 - r_sq) * 1.0
    else:
        fs = 0.04
    # Entropy scoring
    if mean_ent < 3.5:
        es = 0.55 + (3.5 - mean_ent) * 0.12
    else:
        es = 0.06

    combined = ss * 0.40 + fs * 0.30 + es * 0.30
    raw = {"msr_slope": round(slope, 3), "msr_r2": round(r_sq, 3),
           "msr_ent": round(mean_ent, 3)}
    return _c(combined), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 3 — RESIDUAL AUTOCORRELATION (RAC)
# ═══════════════════════════════════════════════════════════

def _s03_rac(gray):
    """
    Real camera noise is spatially independent (white noise) →
    autocorrelation drops to ~0 at lag > 1 pixel.
    Diffusion/GAN noise has correlated structure → autocorrelation
    persists at higher lags.

    Compute: residual → normalise → autocorrelation via FFT
    → mean |autocorrelation| for lags 2–10 in both axes.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    res = gray - blurred
    # Normalise residual to zero-mean unit-variance
    std = float(np.std(res))
    if std < 1e-8:
        return 0.85, {"rac_mean_corr": 1.0}
    res_n = (res - np.mean(res)) / std

    h, w = res_n.shape
    # Row-wise autocorrelation via FFT (efficient O(n log n))
    # Take a central row slice to keep it fast
    mid = h // 2
    row = res_n[mid, :]
    n = len(row)
    fft_r = np.fft.fft(row, n=2 * n)
    acf_row = np.fft.ifft(fft_r * np.conj(fft_r)).real[:n]
    acf_row /= (acf_row[0] + 1e-12)

    # Column-wise
    col = res_n[:, w // 2]
    m = len(col)
    fft_c = np.fft.fft(col, n=2 * m)
    acf_col = np.fft.ifft(fft_c * np.conj(fft_c)).real[:m]
    acf_col /= (acf_col[0] + 1e-12)

    # Mean absolute correlation at lags 2–10
    max_lag = min(11, n, m)
    lag_vals = []
    for lag in range(2, max_lag):
        lag_vals.append(abs(acf_row[lag]))
        lag_vals.append(abs(acf_col[lag]))
    mean_corr = float(np.mean(lag_vals)) if lag_vals else 0.0

    # Natural: mean_corr < 0.05,  Synthetic: > 0.12
    if mean_corr > 0.25:
        s = 0.80 + min((mean_corr - 0.25) * 1.0, 0.20)
    elif mean_corr > 0.12:
        s = 0.45 + (mean_corr - 0.12) * 2.5
    elif mean_corr > 0.06:
        s = 0.20 + (mean_corr - 0.06) * 3.0
    else:
        s = 0.05

    return _c(s), {"rac_mean_corr": round(mean_corr, 4)}


# ═══════════════════════════════════════════════════════════
# SIGNAL 4 — WAVELET BAND ENERGY (WBE)
# ═══════════════════════════════════════════════════════════

def _s04_wbe(gray):
    """
    Single-level Haar DWT → bands LL, LH, HL, HH.

    Features:
     • R_detail = (E_LH + E_HL + E_HH) / E_LL
     • Directional balance D = min(E_LH, E_HL) / max(E_LH, E_HL)
     • HH ratio = E_HH / (E_LH + E_HL + E_HH)
     • Cross-band correlation ρ(LH, HL)

    Diffusion models suppress HH (diagonal) energy and produce
    unnaturally balanced LH/HL bands because convolution kernels
    are isotropic; natural optics + Bayer demosaicing are not.
    """
    if not HAS_PYWT:
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        lv = float(np.var(lap))
        if lv < 50:
            return _c(0.65 + (50 - lv) * 0.006), {"wbe_laplacian_var": round(lv, 2)}
        return 0.12, {"wbe_laplacian_var": round(lv, 2)}

    cA, (cH, cV, cD) = pywt.dwt2(gray, 'haar')

    e_ll = float(np.mean(cA ** 2)) + 1e-12
    e_lh = float(np.mean(cH ** 2)) + 1e-12
    e_hl = float(np.mean(cV ** 2)) + 1e-12
    e_hh = float(np.mean(cD ** 2)) + 1e-12

    r_detail = (e_lh + e_hl + e_hh) / e_ll
    d_bal = min(e_lh, e_hl) / max(e_lh, e_hl)
    hh_ratio = e_hh / (e_lh + e_hl + e_hh)

    # Cross-band correlation LH↔HL
    lh_flat = cH.ravel()
    hl_flat = cV.ravel()
    if np.std(lh_flat) > 1e-10 and np.std(hl_flat) > 1e-10:
        xb_corr = abs(float(np.corrcoef(lh_flat, hl_flat)[0, 1]))
    else:
        xb_corr = 1.0

    s = 0.0
    # Detail ratio
    if r_detail < 0.003:
        s += 0.35
    elif r_detail > 0.30:
        s += 0.15
    else:
        s += 0.04
    # Balance — too symmetric is suspicious
    if d_bal > 0.92:
        s += 0.25
    elif d_bal < 0.30:
        s += 0.20
    else:
        s += 0.04
    # HH suppression
    if hh_ratio < 0.10:
        s += 0.22
    elif hh_ratio > 0.50:
        s += 0.12
    else:
        s += 0.04
    # Cross-band correlation — high = isotropic processing
    if xb_corr > 0.80:
        s += 0.18
    else:
        s += 0.03

    raw = {"wbe_r_detail": round(r_detail, 5), "wbe_balance": round(d_bal, 3),
           "wbe_hh_ratio": round(hh_ratio, 4), "wbe_xb_corr": round(xb_corr, 3)}
    return _c(s), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 5 — FREQUENCY DOMAIN / FFT SLOPE + BAND RATIOS
# ═══════════════════════════════════════════════════════════

def _s05_fft(gray):
    """
    Natural images: P(f) ∝ 1/f^β,  β ≈ 1.5–2.5.

    Additionally partition the radial spectrum into three bands:
      low  (0–20% of max_r)
      mid  (20–60%)
      high (60–100%)
    Diffusion models often over-amplify mid-frequencies relative to
    the natural power-law, producing a "bump" in the mid band.
    """
    h, w = gray.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    f = np.fft.fftshift(np.fft.fft2(gray * win))
    power = np.abs(f) ** 2

    cy, cx = h // 2, w // 2
    max_r = min(cy, cx)
    if max_r < 10:
        return 0.50, {}

    y_idx, x_idx = np.ogrid[-cy:h - cy, -cx:w - cx]
    r_map = np.sqrt(x_idx.astype(np.float64) ** 2 +
                    y_idx.astype(np.float64) ** 2).astype(int)

    radial = np.zeros(max_r)
    for r in range(1, max_r):
        mask = r_map == r
        if np.any(mask):
            radial[r] = np.mean(power[mask])

    # Slope fit (skip DC and tail)
    r_lo, r_hi = 2, max(8, int(max_r * 0.80))
    rr = np.arange(r_lo, r_hi)
    pr = radial[r_lo:r_hi]
    valid = pr > 0
    if np.sum(valid) < 6:
        return 0.50, {}
    log_r = np.log(rr[valid].astype(np.float64))
    log_p = np.log(pr[valid])
    slope, _, r_val, _, _ = sp_stats.linregress(log_r, log_p)
    beta = -slope
    r_sq = r_val ** 2

    # Band energy ratios
    b_low = int(max_r * 0.20)
    b_mid = int(max_r * 0.60)
    e_low = float(np.sum(radial[1:b_low])) + 1e-12
    e_mid = float(np.sum(radial[b_low:b_mid])) + 1e-12
    e_high = float(np.sum(radial[b_mid:])) + 1e-12
    total_e = e_low + e_mid + e_high
    mid_ratio = e_mid / total_e

    # β scoring
    if beta < 0.8:
        bs = 0.50 + (0.8 - beta) * 0.40
    elif beta > 3.5:
        bs = 0.30 + min((beta - 3.5) * 0.10, 0.25)
    elif 1.3 <= beta <= 2.8:
        bs = 0.04
    else:
        bs = 0.18
    # R² scoring
    if r_sq < 0.50:
        rs = 0.40 + (0.50 - r_sq) * 0.50
    elif r_sq < 0.80:
        rs = 0.12 + (0.80 - r_sq) * 0.50
    else:
        rs = 0.04
    # Mid-frequency bump scoring
    # Natural: mid_ratio ≈ 0.30–0.50,  Diffusion: > 0.55
    if mid_ratio > 0.58:
        ms = 0.50 + (mid_ratio - 0.58) * 2.0
    elif mid_ratio > 0.50:
        ms = 0.20 + (mid_ratio - 0.50) * 2.5
    else:
        ms = 0.04

    combined = bs * 0.40 + rs * 0.25 + ms * 0.35
    raw = {"fft_beta": round(beta, 3), "fft_r2": round(r_sq, 3),
           "fft_mid_ratio": round(mid_ratio, 4)}
    return _c(combined * 0.90), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 6 — LOCAL PATCH STATISTICS (LPS)
# ═══════════════════════════════════════════════════════════

def _s06_lps(gray):
    """
    Divide image into non-overlapping 32×32 patches.
    Compute per-patch variance and entropy.
    Measure:
      σ_var   = std of patch variances
      σ_ent   = std of patch entropies
      CV_var  = σ_var / μ_var

    Natural photos: diverse textures → high CV and σ.
    Synthetic: more uniform → low CV and σ.
    """
    h, w = gray.shape
    ph, pw = h // PATCH_SIZE, w // PATCH_SIZE
    if ph < 2 or pw < 2:
        return 0.50, {}

    vars_list = []
    ents_list = []
    for i in range(ph):
        for j in range(pw):
            patch = gray[i * PATCH_SIZE:(i + 1) * PATCH_SIZE,
                         j * PATCH_SIZE:(j + 1) * PATCH_SIZE]
            vars_list.append(float(np.var(patch)))
            ents_list.append(_hist_entropy(patch, bins=64, rng=(0, 255)))

    vars_arr = np.array(vars_list)
    ents_arr = np.array(ents_list)

    mu_var = float(np.mean(vars_arr))
    std_var = float(np.std(vars_arr))
    cv_var = _sd(std_var, mu_var)

    std_ent = float(np.std(ents_arr))
    mean_ent = float(np.mean(ents_arr))

    s = 0.0
    # Variance diversity
    if cv_var < 0.30:
        s += 0.40 + (0.30 - cv_var) * 1.0
    elif cv_var < 0.60:
        s += 0.15 + (0.60 - cv_var) * 0.60
    else:
        s += 0.04
    # Entropy diversity
    if std_ent < 0.30:
        s += 0.30 + (0.30 - std_ent) * 0.80
    elif std_ent < 0.60:
        s += 0.10 + (0.60 - std_ent) * 0.40
    else:
        s += 0.04
    # Overall low variance → blank / synthetic
    if mu_var < 15.0:
        s = max(s, 0.60)

    raw = {"lps_cv_var": round(cv_var, 3), "lps_std_ent": round(std_ent, 3),
           "lps_mean_ent": round(mean_ent, 3)}
    return _c(s), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 7 — GRADIENT & EDGE COHERENCE (GEC)
# ═══════════════════════════════════════════════════════════

def _s07_gec(gray):
    """
    Natural gradient magnitude follows a heavy-tailed distribution
    (high kurtosis κ > 5, positive skewness γ > 1.5).

    Phase congruency proxy: compute gradient phase histogram entropy.
    Edges in natural images span many orientations → high phase entropy.
    AI images may show orientation bias from convolution strides.
    """
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(gx ** 2 + gy ** 2)

    mag_max = float(np.max(mag))
    if mag_max < 1e-6:
        return 0.85, {"gec_kurt": 0.0, "gec_skew": 0.0}

    mag_n = (mag / mag_max).ravel()
    kurt = float(sp_stats.kurtosis(mag_n, fisher=True))
    skew = float(sp_stats.skew(mag_n))

    # Phase (orientation) entropy
    phase = np.arctan2(gy, gx + 1e-12)   # range [−π, π]
    phase_ent = _hist_entropy(phase.ravel(), bins=36, rng=(-np.pi, np.pi))
    max_phase_ent = np.log2(36)
    norm_phase_ent = _sd(phase_ent, max_phase_ent)

    # Kurtosis scoring
    if kurt < 1.5:
        ks = 0.60 + (1.5 - kurt) * 0.15
    elif kurt < 4.0:
        ks = 0.25 + (4.0 - kurt) * 0.10
    elif kurt > 40.0:
        ks = 0.25 + min((kurt - 40.0) * 0.003, 0.20)
    else:
        ks = 0.06
    # Skewness scoring
    if skew < 0.5:
        sw = 0.50 + (0.5 - skew) * 0.30
    elif skew > 6.0:
        sw = 0.20 + min((skew - 6.0) * 0.04, 0.20)
    else:
        sw = 0.06
    # Phase entropy — low = orientation bias
    if norm_phase_ent < 0.60:
        ps = 0.40 + (0.60 - norm_phase_ent) * 0.80
    elif norm_phase_ent < 0.80:
        ps = 0.15 + (0.80 - norm_phase_ent) * 0.60
    else:
        ps = 0.04

    combined = ks * 0.35 + sw * 0.30 + ps * 0.35
    raw = {"gec_kurt": round(kurt, 2), "gec_skew": round(skew, 2),
           "gec_phase_ent": round(norm_phase_ent, 3)}
    return _c(combined), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 8 — RGB CHANNEL RESIDUAL DIVERGENCE (RCD)
# ═══════════════════════════════════════════════════════════

def _s08_rcd(bgr):
    """
    Camera sensors (Bayer CFA) introduce independent noise per colour
    channel → low inter-channel noise correlation and high KL divergence.
    Neural networks process all channels jointly → highly correlated
    residuals and low KL divergence.

    Features:
     • Mean |Pearson ρ| across R-G, R-B, G-B residuals
     • Mean symmetric KL divergence between residual distributions
    """
    channels = [bgr[:, :, i].astype(np.float64) for i in range(3)]
    residuals = []
    for ch in channels:
        residuals.append((ch - cv2.GaussianBlur(ch, (0, 0), sigmaX=2.0)).ravel())

    # Pearson correlations
    def _corr(a, b):
        if np.std(a) < 1e-10 or np.std(b) < 1e-10:
            return 1.0
        return abs(float(np.corrcoef(a, b)[0, 1]))

    pairs = [(0, 1), (0, 2), (1, 2)]
    corrs = [_corr(residuals[i], residuals[j]) for i, j in pairs]
    mean_corr = float(np.mean(corrs))

    # Symmetric KL divergence between residual histograms
    def _sym_kl(a, b):
        h_a, _ = np.histogram(a, bins=128, range=(-60, 60))
        h_b, _ = np.histogram(b, bins=128, range=(-60, 60))
        # Add Laplace smoothing
        h_a = (h_a + 1).astype(np.float64)
        h_b = (h_b + 1).astype(np.float64)
        p = h_a / h_a.sum()
        q = h_b / h_b.sum()
        kl_pq = float(np.sum(p * np.log(p / q)))
        kl_qp = float(np.sum(q * np.log(q / p)))
        return (kl_pq + kl_qp) / 2.0

    kl_vals = [_sym_kl(residuals[i], residuals[j]) for i, j in pairs]
    mean_kl = float(np.mean(kl_vals))

    # Correlation scoring — high = synthetic
    if mean_corr > 0.70:
        cs = 0.70 + (mean_corr - 0.70) * 1.0
    elif mean_corr > 0.50:
        cs = 0.35 + (mean_corr - 0.50) * 1.5
    elif mean_corr > 0.35:
        cs = 0.12 + (mean_corr - 0.35) * 1.2
    else:
        cs = 0.06

    # KL divergence scoring — low = synthetic (channels too similar)
    if mean_kl < 0.005:
        ks = 0.65 + (0.005 - mean_kl) * 60.0
    elif mean_kl < 0.02:
        ks = 0.30 + (0.02 - mean_kl) * 20.0
    elif mean_kl < 0.05:
        ks = 0.10 + (0.05 - mean_kl) * 4.0
    else:
        ks = 0.05

    combined = cs * 0.55 + ks * 0.45
    raw = {"rcd_mean_corr": round(mean_corr, 4), "rcd_mean_kl": round(mean_kl, 5)}
    return _c(combined), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 9 — PIXEL-LEVEL OUTLIER ANALYSIS (PLO)
# ═══════════════════════════════════════════════════════════

def _s09_plo(gray):
    """
    Compute local mean and local standard deviation using a 5×5
    neighbourhood.  For each pixel, compute the z-score:
         z = |pixel − local_mean| / (local_std + ε)

    Natural images: occasional high-z pixels at edges (few outliers).
    Over-smoothed AI images: very few outliers (z > 3 nearly absent).
    Over-sharpened composites: many high-z pixels.

    Feature: fraction of pixels with z > 3 (outlier_rate).
    """
    k = 5
    local_mean = uniform_filter(gray, size=k)
    local_sq_mean = uniform_filter(gray ** 2, size=k)
    local_var = local_sq_mean - local_mean ** 2
    local_var = np.maximum(local_var, 0.0)
    local_std = np.sqrt(local_var) + 1e-8

    z = np.abs(gray - local_mean) / local_std
    outlier_rate = float(np.mean(z > 3.0))

    # Natural photos: outlier_rate ≈ 0.02 – 0.08
    # Over-smoothed (diffusion): < 0.01
    # Over-sharpened (composite): > 0.12
    if outlier_rate < 0.005:
        s = 0.55 + (0.005 - outlier_rate) * 50.0
    elif outlier_rate < 0.012:
        s = 0.25 + (0.012 - outlier_rate) * 25.0
    elif outlier_rate > 0.15:
        s = 0.40 + min((outlier_rate - 0.15) * 3.0, 0.30)
    elif outlier_rate > 0.10:
        s = 0.20 + (outlier_rate - 0.10) * 3.0
    else:
        s = 0.06

    raw = {"plo_outlier_rate": round(outlier_rate, 5)}
    return _c(s), raw


# ═══════════════════════════════════════════════════════════
# SIGNAL 10 — BACKGROUND CONSISTENCY CHECK (BCC)
# ═══════════════════════════════════════════════════════════

def _s10_bcc(bgr, gray):
    """
    Simple fg/bg segmentation via K-means (k=2) on colour.
    Compare: texture variance in fg vs bg.

    Natural photos: background has varying texture (foliage, sky
    gradients, out-of-focus bokeh with noise).
    AI images: backgrounds are often unnaturally smooth and uniform.

    Feature: variance_contrast_ratio = var_fg / (var_bg + ε).
    High ratio → background much smoother than foreground → suspicious.
    """
    h, w = bgr.shape[:2]
    # Downsample for speed
    scale = min(1.0, 256.0 / max(h, w))
    if scale < 1.0:
        small = cv2.resize(bgr, (int(w * scale), int(h * scale)))
        small_gray = cv2.resize(gray, (int(w * scale), int(h * scale)))
    else:
        small = bgr
        small_gray = gray

    pixels = small.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, _ = cv2.kmeans(pixels, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    labels = labels.ravel()

    mask0 = labels.reshape(small_gray.shape) == 0
    mask1 = ~mask0

    # Ensure mask0 is the larger region (background)
    if np.sum(mask0) < np.sum(mask1):
        mask0, mask1 = mask1, mask0

    var_bg = float(np.var(small_gray[mask0])) if np.sum(mask0) > 10 else 1e-6
    var_fg = float(np.var(small_gray[mask1])) if np.sum(mask1) > 10 else 1e-6

    # Variance contrast ratio
    vcr = _sd(var_fg, var_bg + 1e-6)

    # High VCR = background much smoother than foreground → suspicious
    # But also account for natural shallow DOF (moderate VCR is OK)
    if vcr > 12.0:
        s = 0.55 + min((vcr - 12.0) * 0.03, 0.30)
    elif vcr > 6.0:
        s = 0.25 + (vcr - 6.0) * 0.04
    elif vcr < 0.2:
        # Background MORE textured than foreground? Unusual too
        s = 0.25
    else:
        s = 0.06

    # Additional: absolute background variance check
    # Very low bg variance even without contrast → suspicious
    if var_bg < 10.0:
        s = max(s, 0.40 + (10.0 - var_bg) * 0.020)

    raw = {"bcc_vcr": round(vcr, 3), "bcc_var_bg": round(var_bg, 2)}
    return _c(s), raw


# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

def authenticity_check(image_bytes: bytes) -> dict:
    """
    Run the full 10-signal forensic screening with nonlinear decision fusion.

    Returns
    -------
    dict  with keys:
        passed, risk_score, threshold, signals, co_occurrence_count,
        dominant_anomalies, failure_reason
    """
    empty_signals = {
        "ela_score": 0.0,
        "multi_scale_residual_score": 0.0,
        "residual_autocorrelation_score": 0.0,
        "wavelet_band_energy_score": 0.0,
        "fft_spectral_score": 0.0,
        "local_patch_stats_score": 0.0,
        "gradient_edge_score": 0.0,
        "rgb_channel_divergence_score": 0.0,
        "pixel_outlier_score": 0.0,
        "background_consistency_score": 0.0,
    }

    def _fail(reason):
        return {
            "passed": False, "risk_score": 1.0, "threshold": RISK_THRESHOLD,
            "signals": empty_signals, "co_occurrence_count": 0,
            "dominant_anomalies": [], "failure_reason": reason,
        }

    # ── Load ──
    try:
        bgr, pil_img, gray = _load_and_prepare(image_bytes)
    except ValueError as e:
        return _fail(f"Image validation failed: {e}")
    except Exception as e:
        return _fail(f"Corrupt or unreadable image: {e}")

    w, h = pil_img.size
    print(f"[AUTHENTICITY] Analysing {w}x{h} image ...")

    # ── Compute all 10 signals (graceful degradation) ──
    def _safe(fn, *args, name="?"):
        try:
            return fn(*args)
        except Exception as e:
            print(f"[AUTHENTICITY] {name} error: {e}")
            return 0.50, {}

    s_ela,  r_ela  = _safe(_s01_ela, pil_img, name="ELA")
    s_msr,  r_msr  = _safe(_s02_msr, gray, name="MSR")
    s_rac,  r_rac  = _safe(_s03_rac, gray, name="RAC")
    s_wbe,  r_wbe  = _safe(_s04_wbe, gray, name="WBE")
    s_fft,  r_fft  = _safe(_s05_fft, gray, name="FFT")
    s_lps,  r_lps  = _safe(_s06_lps, gray, name="LPS")
    s_gec,  r_gec  = _safe(_s07_gec, gray, name="GEC")
    s_rcd,  r_rcd  = _safe(_s08_rcd, bgr,  name="RCD")
    s_plo,  r_plo  = _safe(_s09_plo, gray, name="PLO")
    s_bcc,  r_bcc  = _safe(_s10_bcc, bgr, gray, name="BCC")

    signals = {
        "ela_score":                      round(float(s_ela), 4),
        "multi_scale_residual_score":     round(float(s_msr), 4),
        "residual_autocorrelation_score": round(float(s_rac), 4),
        "wavelet_band_energy_score":      round(float(s_wbe), 4),
        "fft_spectral_score":             round(float(s_fft), 4),
        "local_patch_stats_score":        round(float(s_lps), 4),
        "gradient_edge_score":            round(float(s_gec), 4),
        "rgb_channel_divergence_score":   round(float(s_rcd), 4),
        "pixel_outlier_score":            round(float(s_plo), 4),
        "background_consistency_score":   round(float(s_bcc), 4),
    }

    # ── Step 1: Weighted base score ──
    score_list = [s_ela, s_msr, s_rac, s_wbe, s_fft,
                  s_lps, s_gec, s_rcd, s_plo, s_bcc]
    weight_list = [WEIGHTS["ela"], WEIGHTS["msr"], WEIGHTS["rac"],
                   WEIGHTS["wbe"], WEIGHTS["fft"], WEIGHTS["lps"],
                   WEIGHTS["gec"], WEIGHTS["rcd"], WEIGHTS["plo"],
                   WEIGHTS["bcc"]]
    base_score = sum(s * w for s, w in zip(score_list, weight_list))

    # ── Step 2: Co-occurrence count ──
    high_signals = {k: v for k, v in signals.items() if v > CO_OCC_THRESHOLD}
    co_count = len(high_signals)

    # ── Step 3: Nonlinear co-occurrence amplification ──
    # Only amplify when the base score is already borderline suspicious.
    # A low base score should NOT be inflated just because a few signals
    # individually exceeded the co-occurrence threshold — this avoids
    # false-positiving natural images (e.g. shallow DOF, heavy JPEG, etc.)
    if co_count >= 3 and base_score >= 0.35:
        # Strong amplification: 3+ signals AND already suspicious
        boosted = base_score + SIGMOID_BOOST * (co_count - 1)
        final_score = _sigmoid((boosted - 0.5) * 3.5)
    elif co_count >= 2 and base_score >= 0.35:
        # Moderate amplification
        bump = 0.06 * co_count
        final_score = min(base_score + bump, 0.95)
    else:
        # No amplification — trust the weighted base score
        final_score = base_score

    final_score = _c(round(final_score, 4))

    # ── Step 4: Hard override rules ──
    # Only apply hard overrides when base_score is already borderline (≥ 0.30)
    # to avoid false-positiving natural images with unusual but legitimate
    # characteristics (e.g. shallow DOF, heavily compressed, etc.)
    hard_reject = False
    hard_reason = ""

    if base_score >= 0.40:
        if s_wbe > 0.80 and s_rcd > 0.70:
            hard_reject = True
            hard_reason = (
                "Hard override: high wavelet band energy symmetry "
                f"({s_wbe:.2f}) combined with cross-channel noise correlation "
                f"({s_rcd:.2f}) — strong synthetic fingerprint."
            )

        if (r_fft.get("fft_mid_ratio", 0) > 0.62 and s_rac > 0.60):
            hard_reject = True
            hard_reason = (
                "Hard override: abnormal mid-frequency amplification "
                f"(mid_ratio={r_fft.get('fft_mid_ratio', 0):.3f}) "
                f"with structured noise persistence (RAC={s_rac:.2f}) "
                "— indicates diffusion-generated content."
            )

    # ── Step 5: Decision ──
    # Identify top-3 dominant anomalies
    sorted_signals = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    dominant = [
        {"signal": k, "score": v, "description": SIGNAL_LABELS.get(k, k)}
        for k, v in sorted_signals[:3]
    ]

    print(f"[AUTHENTICITY] Signals : {signals}")
    print(f"[AUTHENTICITY] Base={base_score:.4f} CoOcc={co_count} "
          f"Final={final_score:.4f} (thr={RISK_THRESHOLD})")

    if hard_reject or final_score > RISK_THRESHOLD:
        # Build explanation from dominant anomalies
        if hard_reject:
            reason = hard_reason
        else:
            top_descs = [d["description"] for d in dominant if d["score"] > 0.40]
            if not top_descs:
                top_descs = [dominant[0]["description"]]
            reason = (
                f"Image failed forensic authenticity screening "
                f"(risk={final_score:.2f}, threshold={RISK_THRESHOLD}). "
                f"Likely synthetic or manipulated. "
                f"Primary indicators: {'; '.join(top_descs)}."
            )

        return {
            "passed": False,
            "risk_score": max(final_score, RISK_THRESHOLD + 0.01) if hard_reject else final_score,
            "threshold": RISK_THRESHOLD,
            "signals": signals,
            "co_occurrence_count": co_count,
            "dominant_anomalies": dominant,
            "failure_reason": reason,
        }

    return {
        "passed": True,
        "risk_score": final_score,
        "threshold": RISK_THRESHOLD,
        "signals": signals,
        "co_occurrence_count": co_count,
        "dominant_anomalies": dominant,
        "failure_reason": "",
    }
