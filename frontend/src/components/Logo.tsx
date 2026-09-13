interface LogoProps {
  size?: number
  withText?: boolean
  tagline?: boolean
  className?: string
}

export default function Logo({ size = 44, withText = true, tagline = false, className = '' }: LogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/assets/logo.png"
        alt="Gyan Sathi logo"
        width={size}
        height={size}
        className="rounded-xl object-contain"
        style={{ width: size, height: size }}
      />
      {withText && (
        <div className="leading-tight">
          <div className="font-extrabold tracking-tight text-navy-900" style={{ fontSize: size * 0.42 }}>
            Gyan <span className="text-brand-orange">Sathi</span>
          </div>
          {tagline && (
            <div className="text-xs text-navy-500 font-medium">તમારો અભ્યાસ, અમારો સાથી</div>
          )}
        </div>
      )}
    </div>
  )
}
