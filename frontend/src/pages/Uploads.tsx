import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CloudUpload, Crown, FileText, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { UploadAllowance, UploadItem } from '../types'

export default function Uploads() {
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const [allowance, setAllowance] = useState<UploadAllowance | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = () =>
    api<{ uploads: UploadItem[]; allowance: UploadAllowance }>('/api/uploads')
      .then((r) => {
        setUploads(r.uploads)
        setAllowance(r.allowance)
      })
      .catch(() => {})

  useEffect(() => {
    load()
  }, [])

  const onFile = async (file: File) => {
    setBusy(true)
    setError('')
    const fd = new FormData()
    fd.append('file', file)
    try {
      await api('/api/uploads', { method: 'POST', body: fd })
      await load()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id: string) => {
    if (!confirm('ડિલીટ કરાય પછી મફત મર્યાદા પરત મળતી નથી. ડિલીટ કરવું છે?')) return
    await api(`/api/uploads/${id}`, { method: 'DELETE' })
    load()
  }

  const limitReached = allowance && !allowance.can_upload

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
      <h1 className="text-lg font-bold text-navy-900">મારી ફાઇલો 📁</h1>

      {/* Allowance card */}
      <div className="bg-white rounded-2xl shadow-card p-5">
        <div className="flex justify-between text-sm mb-2">
          <span className="font-medium text-navy-700">અપલોડ વપરાશ</span>
          <span className="text-navy-400">
            {allowance ? `${allowance.used} / ${allowance.limit === -1 ? 'અસીમિત' : allowance.limit}` : '…'}
          </span>
        </div>
        {allowance && allowance.limit >= 0 && (
          <div className="h-2.5 rounded-full bg-navy-100 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                (allowance.used / allowance.limit) > 0.8 ? 'bg-red-400' : 'bg-brand-green'
              }`}
              style={{ width: `${Math.min(100, (allowance.used / allowance.limit) * 100)}%` }}
            />
          </div>
        )}
        {limitReached && (
          <div className="mt-3 rounded-xl bg-amber-50 border border-amber-200 p-3 text-center space-y-2">
            <div className="text-sm font-semibold text-amber-800">
              તમારા {allowance.limit} મફત uploads પૂર્ણ થઈ ગયા છે.
            </div>
            <Link
              to="/premium"
              className="inline-flex items-center gap-1.5 rounded-xl bg-brand-orange text-white px-4 py-2 text-sm font-bold"
            >
              <Crown size={15} /> Upgrade to Premium
            </Link>
          </div>
        )}
      </div>

      {/* Upload zone */}
      <label
        className={`block border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition ${
          limitReached
            ? 'border-navy-100 opacity-50 cursor-not-allowed'
            : 'border-brand-blue/40 hover:border-brand-blue hover:bg-navy-50/50'
        }`}
      >
        <input
          type="file"
          hidden
          disabled={!!limitReached || busy}
          accept=".pdf,.png,.jpg,.jpeg,.txt,.md,.docx"
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
        <CloudUpload className="mx-auto text-brand-blue" size={34} />
        <div className="mt-2 text-sm font-semibold text-navy-800">
          {busy ? 'અપલોડ થઈ રહ્યું છે…' : 'ફાઇલ અપલોડ કરવા ક્લિક કરો'}
        </div>
        <div className="text-xs text-navy-400 mt-1">PDF, DOCX, TXT, MD અથવા ઇમેજ · મહત્તમ 10MB</div>
      </label>
      {error && <div className="rounded-xl bg-red-50 text-red-600 text-xs px-3 py-2">{error}</div>}

      {/* List */}
      <div className="space-y-2">
        {uploads.map((u) => (
          <div key={u.id} className="bg-white rounded-2xl shadow-card p-3.5 flex items-center gap-3">
            <FileText size={18} className="text-brand-blue shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-navy-900 truncate">{u.original_name}</div>
              <div className="text-[11px] text-navy-400">
                {(u.file_size / 1024).toFixed(0)} KB ·{' '}
                {u.created_at ? new Date(u.created_at).toLocaleDateString('gu-IN') : ''} ·{' '}
                {u.analysis_status === 'completed' ? '✓ વિશ્લેષણ થયું' : '⏳'}
              </div>
            </div>
            <button onClick={() => remove(u.id)} className="p-2 rounded-lg text-red-400 hover:bg-red-50">
              <Trash2 size={15} />
            </button>
          </div>
        ))}
        {uploads.length === 0 && (
          <div className="text-center text-sm text-navy-400 bg-white rounded-2xl p-8 shadow-card">
            હજી કોઈ ફાઇલ અપલોડ નથી.
          </div>
        )}
      </div>

      <p className="text-[11px] text-navy-300 text-center">
        નોંધ: ફાઇલ ડિલીટ કરવાથી મફત અપલોડ મર્યાદા પરત મળતી નથી (વપરાશ આધારિત છે).
      </p>
    </div>
  )
}
