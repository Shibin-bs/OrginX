import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const BASE = 'http://localhost:8000'
const api = axios.create({ baseURL: BASE })

const styles = {
  app: { minHeight: '100vh', background: '#030712', color: '#c8d8e8', fontFamily: 'Courier New, monospace' },
  header: { borderBottom: '1px solid rgba(0,245,255,0.2)', padding: '20px 32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0,245,255,0.03)' },
  logo: { fontSize: '2rem', color: '#00F5FF', letterSpacing: '0.3em', fontWeight: 'bold' },
  tagline: { fontSize: '0.7rem', color: '#3a6a7a', letterSpacing: '0.2em', marginTop: 4 },
  statusDot: (ok) => ({ width: 8, height: 8, borderRadius: '50%', background: ok ? '#00FF85' : '#FF2D55', display: 'inline-block', marginRight: 8 }),
  nav: { display: 'flex', gap: 0, borderBottom: '1px solid rgba(0,245,255,0.1)', background: 'rgba(0,0,0,0.3)' },
  tab: (active) => ({ padding: '12px 28px', cursor: 'pointer', background: 'transparent', border: 'none', borderBottom: active ? '2px solid #00F5FF' : '2px solid transparent', color: active ? '#00F5FF' : '#5a7a8a', fontFamily: 'Courier New, monospace', fontSize: '0.85rem', letterSpacing: '0.15em', textTransform: 'uppercase' }),
  main: { maxWidth: 800, margin: '40px auto', padding: '0 24px' },
  card: { background: 'rgba(0,245,255,0.04)', border: '1px solid rgba(0,245,255,0.15)', padding: 28, marginBottom: 20 },
  cardRed: { background: 'rgba(255,45,85,0.06)', border: '1px solid rgba(255,45,85,0.3)', padding: 28, marginBottom: 20 },
  cardGreen: { background: 'rgba(0,255,133,0.06)', border: '1px solid rgba(0,255,133,0.3)', padding: 28, marginBottom: 20 },
  label: { display: 'block', color: '#00b8c4', fontSize: '0.7rem', letterSpacing: '0.2em', textTransform: 'uppercase', marginBottom: 8 },
  input: { width: '100%', background: 'rgba(0,245,255,0.03)', border: '1px solid rgba(0,245,255,0.2)', color: '#c8d8e8', padding: '10px 14px', fontFamily: 'Courier New, monospace', fontSize: '0.9rem', outline: 'none', marginBottom: 16 },
  btn: { background: 'transparent', border: '1px solid #00F5FF', color: '#00F5FF', padding: '10px 28px', fontFamily: 'Courier New, monospace', fontSize: '0.9rem', cursor: 'pointer', letterSpacing: '0.1em', marginRight: 10 },
  btnRed: { background: 'transparent', border: '1px solid #FF2D55', color: '#FF2D55', padding: '10px 28px', fontFamily: 'Courier New, monospace', fontSize: '0.9rem', cursor: 'pointer', letterSpacing: '0.1em' },
  title: { fontSize: '1.4rem', color: '#00F5FF', letterSpacing: '0.15em', marginBottom: 16 },
  hash: { background: 'rgba(0,0,0,0.5)', border: '1px solid rgba(0,245,255,0.1)', padding: 12, fontFamily: 'Courier New, monospace', fontSize: '0.75rem', color: '#00b8c4', wordBreak: 'break-all', marginBottom: 12 },
  row: { display: 'flex', gap: 12, marginBottom: 16 },
  signal: { flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(0,245,255,0.1)', padding: 16, textAlign: 'center' },
  signalVal: (v) => ({ fontSize: '1.8rem', fontWeight: 'bold', color: v > 0.6 ? '#FF2D55' : v > 0.4 ? '#FFB800' : '#00FF85' }),
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '8px 12px', borderBottom: '1px solid rgba(0,245,255,0.15)', color: '#00b8c4', fontSize: '0.75rem', textAlign: 'left', letterSpacing: '0.1em' },
  td: { padding: '10px 12px', borderBottom: '1px solid rgba(0,245,255,0.05)', fontSize: '0.8rem', fontFamily: 'Courier New, monospace' },
  error: { color: '#FF2D55', fontSize: '0.8rem', marginBottom: 12, padding: '8px 12px', background: 'rgba(255,45,85,0.1)', border: '1px solid rgba(255,45,85,0.3)' },
  dropzone: { border: '2px dashed rgba(0,245,255,0.2)', padding: 40, textAlign: 'center', cursor: 'pointer', marginBottom: 16 },
}

// ── DASHBOARD ──────────────────────────────────────────
function Dashboard() {
  const [health, setHealth] = useState(null)
  const [registry, setRegistry] = useState(null)

  useEffect(() => {
    api.get('/api/health').then(r => setHealth(r.data)).catch(() => setHealth({ status: 'error' }))
    api.get('/api/consent/registry').then(r => setRegistry(r.data)).catch(() => { })
  }, [])

  return (
    <div>
      <div style={styles.card}>
        <div style={styles.title}>SYSTEM STATUS</div>
        <div style={{ display: 'flex', gap: 40, marginBottom: 20 }}>
          <div>
            <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 6 }}>BACKEND</div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span style={styles.statusDot(health?.status === 'ok')} />
              <span style={{ color: health?.status === 'ok' ? '#00FF85' : '#FF2D55', fontSize: '0.9rem' }}>
                {health?.status === 'ok' ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
          </div>
          <div>
            <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 6 }}>REGISTERED USERS</div>
            <div style={{ color: '#00F5FF', fontSize: '1.8rem', fontWeight: 'bold' }}>{registry?.total ?? '—'}</div>
          </div>
          <div>
            <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 6 }}>VERSION</div>
            <div style={{ color: '#00F5FF', fontSize: '0.9rem' }}>{health?.version ?? '—'}</div>
          </div>
        </div>
        {health?.merkle_root && (
          <>
            <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 6 }}>MERKLE ROOT</div>
            <div style={styles.hash}>{health.merkle_root}</div>
          </>
        )}
      </div>

      <div style={styles.card}>
        <div style={styles.title}>CONSENT REGISTRY</div>
        {!registry?.records?.length ? (
          <div style={{ color: '#5a7a8a', textAlign: 'center', padding: 20 }}>No identities registered yet</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>HANDLE</th>
                <th style={styles.th}>KEY HASH</th>
                <th style={styles.th}>REGISTERED</th>
                <th style={styles.th}>MEDIA</th>
              </tr>
            </thead>
            <tbody>
              {registry.records.map(r => (
                <tr key={r.id}>
                  <td style={{ ...styles.td, color: '#00F5FF' }}>@{r.user_handle}</td>
                  <td style={{ ...styles.td, color: '#5a7a8a' }}>{r.public_key_hash}</td>
                  <td style={styles.td}>{new Date(r.registered_at).toLocaleString()}</td>
                  <td style={{ ...styles.td, color: '#FFB800' }}>{r.media_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── REGISTER ───────────────────────────────────────────
function Register() {
  const [handle, setHandle] = useState('')
  const [seed, setSeed] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const generateSeed = () => {
    const arr = new Uint8Array(16)
    crypto.getRandomValues(arr)
    setSeed(Array.from(arr).map(b => b.toString(16).padStart(2, '0')).join(''))
  }

  const submit = async () => {
    if (!handle || !seed) { setError('Both fields are required'); return }
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await api.post('/api/consent/register', { user_handle: handle, watermark_seed: seed })
      setResult(res.data)
    } catch (e) {
      setError(e.response?.data?.detail || 'Registration failed')
    } finally { setLoading(false) }
  }

  return (
    <div>
      <div style={styles.card}>
        <div style={styles.title}>REGISTER IDENTITY</div>
        <div style={{ color: '#5a7a8a', fontSize: '0.8rem', marginBottom: 20, lineHeight: 1.6 }}>
          Register your identity on OriginX. Your watermark seed will be embedded invisibly into your media.
        </div>

        <label style={styles.label}>User Handle</label>
        <input style={styles.input} placeholder="e.g. your_name" value={handle} onChange={e => setHandle(e.target.value)} />

        <label style={styles.label}>Watermark Seed</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <input style={{ ...styles.input, marginBottom: 0, flex: 1, letterSpacing: '0.05em' }} placeholder="32 character hex string" value={seed} onChange={e => setSeed(e.target.value)} />
          <button style={styles.btn} onClick={generateSeed}>GENERATE</button>
        </div>
        <div style={{ color: '#3a5a6a', fontSize: '0.7rem', marginBottom: 16 }}>Keep this seed secret. It is your cryptographic identity.</div>

        {error && <div style={styles.error}>⚠ {error}</div>}
        <button style={styles.btn} onClick={submit} disabled={loading}>
          {loading ? 'REGISTERING...' : '⛓ REGISTER'}
        </button>
      </div>

      {result && (
        <div style={styles.cardGreen}>
          <div style={{ color: '#00FF85', fontSize: '1rem', letterSpacing: '0.15em', marginBottom: 16 }}>✓ IDENTITY REGISTERED</div>
          <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 4 }}>Public Key Hash</div>
          <div style={styles.hash}>{result.public_key_hash}</div>
          <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 4 }}>Merkle Root</div>
          <div style={styles.hash}>{result.merkle_root}</div>
          <button style={styles.btn} onClick={() => navigator.clipboard.writeText(result.public_key_hash)}>
            COPY HASH
          </button>
        </div>
      )}
    </div>
  )
}

// ── WATERMARK ──────────────────────────────────────────
function Watermark() {
  const [subTab, setSubTab] = useState('embed')

  // ── Embed state ──
  const [embedFile, setEmbedFile] = useState(null)
  const [handle, setHandle] = useState('')
  const [embedError, setEmbedError] = useState('')

  // Step 1: Verify
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [verifyResult, setVerifyResult] = useState(null)  // null | { verified, signals, ... }
  const [verifyFailed, setVerifyFailed] = useState(null)  // null | { message, analysis?, duplicate_info? }

  // Step 2: Consent
  const [consentChecked, setConsentChecked] = useState(false)

  // Step 3: Embed
  const [embedLoading, setEmbedLoading] = useState(false)
  const [embedResult, setEmbedResult] = useState('')

  // ── Extract state ──
  const [extractFile, setExtractFile] = useState(null)
  const [extractResult, setExtractResult] = useState(null)
  const [extractLoading, setExtractLoading] = useState(false)

  const embedRef = useRef()
  const extractRef = useRef()

  // Reset all embed state when a new file is selected
  const handleEmbedFile = (f) => {
    setEmbedFile(f)
    setVerifyResult(null)
    setVerifyFailed(null)
    setConsentChecked(false)
    setEmbedResult('')
    setEmbedError('')
  }

  // Step 1: Verify image authenticity
  const doVerify = async () => {
    if (!embedFile || !handle) { setEmbedError('Select image and enter handle'); return }
    setVerifyLoading(true); setEmbedError(''); setVerifyResult(null); setVerifyFailed(null)
    setConsentChecked(false); setEmbedResult('')
    try {
      const fd = new FormData()
      fd.append('file', embedFile)
      fd.append('user_handle', handle)
      const res = await api.post('/api/watermark/verify', fd)
      setVerifyResult(res.data)
    } catch (e) {
      const detail = e.response?.data?.detail
      if (detail && typeof detail === 'object') {
        setVerifyFailed(detail)
      } else {
        setVerifyFailed({ message: detail || 'Verification failed. Please try again.' })
      }
    } finally { setVerifyLoading(false) }
  }

  // Step 3: Embed after consent
  const doEmbed = async () => {
    if (!embedFile || !handle || !consentChecked) return
    setEmbedLoading(true); setEmbedError('')
    try {
      const fd = new FormData()
      fd.append('file', embedFile)
      fd.append('user_handle', handle)
      fd.append('consent_accepted', 'true')
      const res = await api.post('/api/watermark/embed', fd, { responseType: 'blob' })
      setEmbedResult(URL.createObjectURL(res.data))
    } catch (e) {
      let errorMsg = 'Embedding failed'
      try {
        // When responseType is 'blob', error responses are also Blob objects
        // We need to read the blob as text and parse it as JSON
        if (e.response?.data instanceof Blob) {
          const text = await e.response.data.text()
          const json = JSON.parse(text)
          const detail = json.detail
          errorMsg = typeof detail === 'object' ? detail.message : (detail || errorMsg)
        } else {
          const detail = e.response?.data?.detail
          errorMsg = typeof detail === 'object' ? detail.message : (detail || errorMsg)
        }
      } catch (_) { /* keep default error */ }
      setEmbedError(errorMsg)
    } finally { setEmbedLoading(false) }
  }

  const doExtract = async () => {
    if (!extractFile) return
    setExtractLoading(true)
    try {
      const fd = new FormData()
      fd.append('file', extractFile)
      const res = await api.post('/api/watermark/extract', fd)
      setExtractResult(res.data)
    } catch (e) { setExtractResult({ found: false }) }
    finally { setExtractLoading(false) }
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 0, marginBottom: 20 }}>
        {['embed', 'extract'].map(t => (
          <button key={t} style={styles.tab(subTab === t)} onClick={() => setSubTab(t)}>
            {t === 'embed' ? '⬇ EMBED' : '⬆ EXTRACT'}
          </button>
        ))}
      </div>

      {subTab === 'embed' && (
        <div>
          {/* Upload + Handle */}
          <div style={styles.card}>
            <div style={styles.title}>EMBED WATERMARK</div>
            <div style={{ color: '#5a7a8a', fontSize: '0.78rem', marginBottom: 16, lineHeight: 1.6 }}>
              Three-step verification: Authenticity Check → Ownership Declaration → Watermark Embedding
            </div>
            <div style={styles.dropzone} onClick={() => embedRef.current.click()}>
              <input ref={embedRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => e.target.files[0] && handleEmbedFile(e.target.files[0])} />
              {embedFile ? (
                <div style={{ color: '#00FF85' }}>✓ {embedFile.name}</div>
              ) : (
                <div style={{ color: '#5a7a8a' }}>Click to select image</div>
              )}
            </div>
            <label style={styles.label}>Your Registered Handle</label>
            <input style={styles.input} placeholder="e.g. your_name" value={handle} onChange={e => setHandle(e.target.value)} />
            {embedError && <div style={styles.error}>⚠ {embedError}</div>}

            {/* Step 1: Verify Button (only when no result yet) */}
            {!verifyResult && !embedResult && (
              <button style={styles.btn} onClick={doVerify} disabled={verifyLoading || !embedFile || !handle}>
                {verifyLoading ? 'ANALYZING...' : '◎ VERIFY IMAGE'}
              </button>
            )}
          </div>

          {/* Verification FAILED */}
          {verifyFailed && (
            <div style={styles.cardRed}>
              <div style={{ color: '#FF2D55', fontSize: '1.1rem', letterSpacing: '0.1em', marginBottom: 12 }}>
                ✗ IMAGE REJECTED
              </div>
              <div style={{ color: '#c8d8e8', fontSize: '0.85rem', lineHeight: 1.6, marginBottom: 16 }}>
                {verifyFailed.message}
              </div>

              {/* Show duplicate info */}
              {verifyFailed.duplicate_info && (
                <div style={{ padding: '12px 16px', background: 'rgba(255,45,85,0.1)', border: '1px solid rgba(255,45,85,0.3)', marginBottom: 12 }}>
                  <div style={{ color: '#FF2D55', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 8 }}>⚠ FRAUD ALERT</div>
                  <div style={{ color: '#c8d8e8', fontSize: '0.82rem' }}>
                    Registered by: <span style={{ color: '#00F5FF', fontWeight: 'bold' }}>{verifyFailed.duplicate_info.already_registered_by}</span>
                  </div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.78rem', marginTop: 4 }}>
                    Match type: {verifyFailed.duplicate_info.match_type}
                    {verifyFailed.duplicate_info.similarity && ` (${verifyFailed.duplicate_info.similarity})`}
                  </div>
                </div>
              )}

              {/* Show forensic signals */}
              {verifyFailed.analysis?.signals && (
                <div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 10 }}>FORENSIC SIGNALS</div>
                  <div style={styles.row}>
                    {Object.entries(verifyFailed.analysis.signals).map(([key, value]) => (
                      <div key={key} style={styles.signal}>
                        <div style={{ color: '#5a7a8a', fontSize: '0.65rem', marginBottom: 6 }}>{key.replace(/_/g, ' ').toUpperCase()}</div>
                        <div style={styles.signalVal(value)}>{(value * 100).toFixed(1)}%</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.78rem', marginTop: 8 }}>
                    Risk Score: <span style={{ color: '#FF2D55', fontSize: '1.1rem', fontWeight: 'bold' }}>
                      {(verifyFailed.analysis.risk_score * 100).toFixed(1)}%
                    </span>
                    <span style={{ marginLeft: 12 }}>Threshold: {(verifyFailed.analysis.threshold * 100).toFixed(0)}%</span>
                  </div>
                </div>
              )}

              <button style={{ ...styles.btn, marginTop: 16 }} onClick={() => { setVerifyFailed(null); setEmbedFile(null) }}>
                ← TRY DIFFERENT IMAGE
              </button>
            </div>
          )}

          {/* Step 2: Verification PASSED → Show consent */}
          {verifyResult && !embedResult && (
            <div>
              <div style={styles.cardGreen}>
                <div style={{ color: '#00FF85', fontSize: '1.1rem', letterSpacing: '0.1em', marginBottom: 8 }}>
                  ✓ IMAGE VERIFIED AS AUTHENTIC
                </div>
                <div style={{ color: '#c8d8e8', fontSize: '0.82rem', lineHeight: 1.5, marginBottom: 12 }}>
                  This image has passed all forensic authenticity checks. Risk score:{' '}
                  <span style={{ color: '#00FF85', fontWeight: 'bold' }}>{(verifyResult.risk_score * 100).toFixed(1)}%</span>
                </div>

                {/* Show forensic signals in compact form */}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
                  {verifyResult.signals && Object.entries(verifyResult.signals).map(([key, value]) => (
                    <div key={key} style={{ background: 'rgba(0,255,133,0.08)', border: '1px solid rgba(0,255,133,0.15)', padding: '6px 10px', fontSize: '0.7rem' }}>
                      <span style={{ color: '#5a7a8a' }}>{key.replace(/_/g, ' ').replace('score', '').trim()}: </span>
                      <span style={{ color: value > 0.4 ? '#FFB800' : '#00FF85' }}>{(value * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ownership Declaration */}
              <div style={{ ...styles.card, borderColor: 'rgba(255,184,0,0.4)', background: 'rgba(255,184,0,0.04)' }}>
                <div style={{ color: '#FFB800', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 12 }}>
                  ⚖ OWNERSHIP DECLARATION
                </div>
                <div style={{ color: '#c8d8e8', fontSize: '0.82rem', lineHeight: 1.8, marginBottom: 20, padding: '16px 20px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,184,0,0.15)', fontStyle: 'italic' }}>
                  "{verifyResult.ownership_declaration}"
                </div>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', marginBottom: 20 }}>
                  <input
                    type="checkbox"
                    checked={consentChecked}
                    onChange={e => setConsentChecked(e.target.checked)}
                    style={{ width: 18, height: 18, marginTop: 2, accentColor: '#FFB800', cursor: 'pointer' }}
                  />
                  <span style={{ color: '#c8d8e8', fontSize: '0.82rem', lineHeight: 1.5 }}>
                    I have read and I accept the above ownership declaration. I understand that making a false claim
                    constitutes fraud and I shall be liable to face legal consequences.
                  </span>
                </label>

                {embedError && <div style={styles.error}>⚠ {embedError}</div>}

                <button
                  style={consentChecked ? { ...styles.btn, borderColor: '#00FF85', color: '#00FF85' } : { ...styles.btn, opacity: 0.3, cursor: 'not-allowed' }}
                  onClick={doEmbed}
                  disabled={!consentChecked || embedLoading}
                >
                  {embedLoading ? 'EMBEDDING...' : '◈ ACCEPT & EMBED SIGNATURE'}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Embed result */}
          {embedResult && (
            <div style={styles.cardGreen}>
              <div style={{ color: '#00FF85', fontSize: '1.1rem', letterSpacing: '0.1em', marginBottom: 12 }}>
                ✓ WATERMARK EMBEDDED SUCCESSFULLY
              </div>
              <div style={{ color: '#c8d8e8', fontSize: '0.82rem', lineHeight: 1.5, marginBottom: 16 }}>
                Your ownership declaration has been recorded. The image is now signed with your OriginX identity.
              </div>
              <img src={embedResult} alt="watermarked" style={{ maxWidth: '100%', maxHeight: 300, border: '1px solid rgba(0,255,133,0.3)', display: 'block', marginBottom: 12 }} />
              <div style={{ display: 'flex', gap: 10 }}>
                <a href={embedResult} download="originx_watermarked.png">
                  <button style={styles.btn}>⬇ DOWNLOAD</button>
                </a>
                <button style={styles.btn} onClick={() => { setEmbedFile(null); setVerifyResult(null); setConsentChecked(false); setEmbedResult(''); setEmbedError('') }}>
                  ◈ EMBED ANOTHER
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {subTab === 'extract' && (
        <div style={styles.card}>
          <div style={styles.title}>EXTRACT WATERMARK</div>
          <div style={styles.dropzone} onClick={() => extractRef.current.click()}>
            <input ref={extractRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => setExtractFile(e.target.files[0])} />
            {extractFile ? (
              <div style={{ color: '#00FF85' }}>✓ {extractFile.name}</div>
            ) : (
              <div style={{ color: '#5a7a8a' }}>Click to select image to scan</div>
            )}
          </div>
          <button style={styles.btn} onClick={doExtract} disabled={extractLoading || !extractFile}>
            {extractLoading ? 'SCANNING...' : '◉ SCAN FOR SIGNATURE'}
          </button>
          {extractResult && (
            <div style={{ marginTop: 20, ...(extractResult.found ? styles.cardGreen : styles.card) }}>
              {extractResult.found ? (
                <>
                  <div style={{ color: '#00FF85', fontSize: '1.2rem', marginBottom: 12, letterSpacing: '0.1em' }}>✓ SIGNATURE VERIFIED SUCCESSFULLY</div>
                  <div style={{ color: '#c8d8e8', fontSize: '0.85rem', marginBottom: 16, lineHeight: 1.6 }}>
                    {extractResult.message}
                  </div>
                  <div style={{ display: 'flex', gap: 30, marginBottom: 16, flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 4 }}>MATCHED IDENTITY</div>
                      <div style={{ color: '#00F5FF', fontSize: '1.3rem', fontWeight: 'bold' }}>@{extractResult.matched_user}</div>
                    </div>
                    <div>
                      <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 4 }}>VERIFICATION METHOD</div>
                      <div style={{ color: '#00FF85', fontSize: '0.85rem', fontFamily: 'Courier New' }}>
                        {extractResult.verification_method === 'EXACT_HASH_MATCH' ? '◈ EXACT HASH MATCH' :
                          extractResult.verification_method === 'PERCEPTUAL_HASH_MATCH' ? '◉ PERCEPTUAL HASH MATCH' :
                            '⛓ EMBEDDED WATERMARK'}
                      </div>
                    </div>
                  </div>
                  {extractResult.public_key_hash && (
                    <div style={{ marginBottom: 12 }}>
                      <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 4 }}>PUBLIC KEY HASH</div>
                      <div style={styles.hash}>{extractResult.public_key_hash}</div>
                    </div>
                  )}
                  {extractResult.registered_at && (
                    <div>
                      <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 4 }}>REGISTERED ON</div>
                      <div style={{ color: '#c8d8e8', fontSize: '0.85rem' }}>{new Date(extractResult.registered_at).toLocaleString()}</div>
                    </div>
                  )}
                  {extractResult.similarity && (
                    <div style={{ marginTop: 12 }}>
                      <div style={{ color: '#5a7a8a', fontSize: '0.7rem', letterSpacing: '0.15em', marginBottom: 4 }}>MATCH SIMILARITY</div>
                      <div style={{ color: '#00FF85', fontSize: '1.1rem' }}>{extractResult.similarity}%</div>
                    </div>
                  )}
                </>
              ) : (
                <div>
                  <div style={{ color: '#FF2D55', fontSize: '1rem', marginBottom: 8 }}>◯ NO SIGNATURE DETECTED</div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.85rem' }}>{extractResult.message || 'No OriginX signature detected in this image'}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── ANALYZE ────────────────────────────────────────────
function Analyze() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef()

  const handleFile = (f) => {
    setFile(f)
    setResult(null)
    const reader = new FileReader()
    reader.onload = e => setPreview(e.target.result)
    reader.readAsDataURL(f)
  }

  const analyze = async () => {
    if (!file) return
    setLoading(true); setError(''); setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/api/detect/analyze', fd)
      setResult(res.data)
    } catch (e) { setError('Analysis failed') }
    finally { setLoading(false) }
  }

  return (
    <div>
      <div style={styles.card}>
        <div style={styles.title}>DEEPFAKE ANALYZER</div>
        <div style={{ color: '#5a7a8a', fontSize: '0.8rem', marginBottom: 20 }}>
          Three layer forensic pipeline: Watermark → Frequency Analysis → Gemini AI
        </div>

        <div style={styles.dropzone} onClick={() => fileRef.current.click()}>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => e.target.files[0] && handleFile(e.target.files[0])} />
          {preview ? (
            <img src={preview} alt="preview" style={{ maxHeight: 250, maxWidth: '100%', display: 'block', margin: '0 auto' }} />
          ) : (
            <>
              <div style={{ fontSize: '2rem', marginBottom: 8, opacity: 0.4 }}>◉</div>
              <div style={{ color: '#5a7a8a' }}>Click to upload image for analysis</div>
            </>
          )}
        </div>

        {error && <div style={styles.error}>⚠ {error}</div>}
        <button style={styles.btn} onClick={analyze} disabled={!file || loading}>
          {loading ? 'ANALYZING...' : '⬡ ANALYZE IMAGE'}
        </button>
      </div>

      {result && (
        <div>
          {/* Verdict */}
          <div style={result.is_deepfake ? styles.cardRed : styles.cardGreen}>
            <div style={{ fontSize: '1.5rem', letterSpacing: '0.1em', color: result.is_deepfake ? '#FF2D55' : '#00FF85', marginBottom: 8 }}>
              {result.is_deepfake ? '⚠ SYNTHETIC MEDIA DETECTED' : '✓ AUTHENTIC MEDIA'}
            </div>
            <div style={{ color: '#5a7a8a', fontSize: '0.8rem' }}>
              Confidence: <span style={{ color: result.is_deepfake ? '#FF2D55' : '#00FF85', fontSize: '1.2rem' }}>
                {(result.confidence * 100).toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Signals */}
          <div style={styles.card}>
            <div style={{ color: '#00b8c4', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 16 }}>DETECTION SIGNALS</div>
            <div style={styles.row}>
              {[
                { label: 'ELA Score', value: result.signals?.ela_score },
                { label: 'Noise Score', value: result.signals?.noise_score },
                { label: 'Freq Score', value: result.signals?.freq_score },
              ].map(({ label, value }) => (
                <div key={label} style={styles.signal}>
                  <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 8 }}>{label}</div>
                  <div style={styles.signalVal(value)}>{(value * 100).toFixed(1)}%</div>
                </div>
              ))}
            </div>
          </div>

          {/* Provenance */}
          <div style={result.provenance?.consent_violated ? styles.cardRed : styles.card}>
            <div style={{ color: '#00b8c4', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 12 }}>PROVENANCE REPORT</div>
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: '#5a7a8a', fontSize: '0.8rem' }}>Watermark Found: </span>
              <span style={{ color: result.provenance?.watermark_found ? '#00FF85' : '#5a7a8a' }}>
                {result.provenance?.watermark_found ? 'YES' : 'NO'}
              </span>
            </div>
            {result.provenance?.matched_user && (
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: '#5a7a8a', fontSize: '0.8rem' }}>Matched User: </span>
                <span style={{ color: '#00F5FF' }}>@{result.provenance.matched_user}</span>
              </div>
            )}
            <div style={{ marginBottom: 8 }}>
              <span style={{ color: '#5a7a8a', fontSize: '0.8rem' }}>Detection Type: </span>
              <span style={{ color: result.provenance?.consent_violated ? '#FF2D55' : '#00F5FF', fontFamily: 'Courier New', fontSize: '0.85rem' }}>
                {result.provenance?.detection_type}
              </span>
            </div>
            {result.provenance?.consent_violated && (
              <div style={{ color: '#FF2D55', marginTop: 12, padding: '10px 14px', border: '1px solid rgba(255,45,85,0.3)', fontSize: '0.85rem' }}>
                ⚠ DATA RIGHTS VIOLATION — Consent signature of @{result.provenance.matched_user} detected in synthetic media
              </div>
            )}
          </div>

          {/* Gemini */}
          {result.gemini_analysis && !result.gemini_analysis.error && (
            <div style={styles.card}>
              <div style={{ color: '#00b8c4', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 12 }}>✦ GEMINI AI FORENSICS</div>
              <div style={{ color: '#c8d8e8', fontSize: '0.85rem', lineHeight: 1.7, marginBottom: 12, fontStyle: 'italic' }}>
                "{result.gemini_analysis.summary}"
              </div>
              <div style={{ display: 'flex', gap: 20, marginBottom: 12 }}>
                <div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 4 }}>VERDICT</div>
                  <div style={{ color: result.gemini_analysis.verdict === 'SYNTHETIC' ? '#FF2D55' : '#00FF85', fontFamily: 'Courier New' }}>
                    {result.gemini_analysis.verdict}
                  </div>
                </div>
                <div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 4 }}>METHOD</div>
                  <div style={{ color: '#00F5FF', fontFamily: 'Courier New' }}>{result.gemini_analysis.probable_method}</div>
                </div>
              </div>
              {result.gemini_analysis.artifacts_found?.length > 0 && (
                <div>
                  <div style={{ color: '#5a7a8a', fontSize: '0.7rem', marginBottom: 8 }}>ARTIFACTS DETECTED</div>
                  {result.gemini_analysis.artifacts_found.map((a, i) => (
                    <div key={i} style={{ color: '#8aaabb', fontSize: '0.78rem', marginBottom: 4 }}>▸ {a}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Forensic Report */}
          {result.forensic_report && (
            <div style={styles.card}>
              <div style={{ color: '#00b8c4', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 12 }}>FORENSIC REPORT</div>
              <div style={{ color: '#c8d8e8', fontSize: '0.85rem', lineHeight: 1.8 }}>{result.forensic_report}</div>
            </div>
          )}

          {/* Violation Notice */}
          {result.violation_notice && (
            <div style={styles.cardRed}>
              <div style={{ color: '#FF2D55', fontSize: '0.75rem', letterSpacing: '0.15em', marginBottom: 12 }}>⚠ VIOLATION NOTICE</div>
              <div style={{ color: '#c8d8e8', fontSize: '0.82rem', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{result.violation_notice}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── MAIN APP ───────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState('dashboard')

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <div>
          <div style={styles.logo}>ORIGINX</div>
          <div style={styles.tagline}>WHOSE REALITY WAS STOLEN?</div>
        </div>
        <div style={{ fontSize: '0.7rem', color: '#3a6a7a', letterSpacing: '0.15em' }}>
          DATA DIGNITY INFRASTRUCTURE
        </div>
      </header>

      <nav style={styles.nav}>
        {[
          { id: 'dashboard', label: '◈ DASHBOARD' },
          { id: 'register', label: '⛓ REGISTER' },
          { id: 'watermark', label: '◉ WATERMARK' },
          { id: 'analyze', label: '⬡ ANALYZE' },
        ].map(t => (
          <button key={t.id} style={styles.tab(tab === t.id)} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main style={styles.main}>
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'register' && <Register />}
        {tab === 'watermark' && <Watermark />}
        {tab === 'analyze' && <Analyze />}
      </main>
    </div>
  )
}