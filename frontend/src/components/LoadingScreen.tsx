import Logo from './Logo'

export default function LoadingScreen() {
  return (
    <div className="h-full flex flex-col items-center justify-center gap-4 bg-white">
      <div className="animate-pulse">
        <Logo size={72} withText={false} />
      </div>
      <div className="text-navy-700 font-semibold">Gyan Sathi લોડ થઈ રહ્યું છે…</div>
      <div className="text-xs text-navy-400">તમારો અભ્યાસ, અમારો સાથી</div>
    </div>
  )
}
