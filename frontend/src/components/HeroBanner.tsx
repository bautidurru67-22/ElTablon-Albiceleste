import styles from './HeroBanner.module.css'

// Textos configurables — en el futuro desde CMS o env
const CLAIMS = [
  'DONDE JUEGA ARGENTINA',
  'TODOS JUNTOS, DONDE ESTÉ ARGENTINA',
] as const

interface HeroBannerProps {
  claimIndex?: 0 | 1
}

export default function HeroBanner({ claimIndex = 0 }: HeroBannerProps) {
  return (
    <div className={styles.wrapper}>
      {/* Franja principal */}
      <div className={styles.banner}>
        <div className={styles.stripeLight} />
        <div className={styles.stripeBlue} />
        <div className={styles.stripeLight} />

        <div className={styles.content}>
          <p className={styles.claim}>{CLAIMS[claimIndex]}</p>
        </div>
      </div>

      {/* Slot publicitario — oculto hasta tener anunciante */}
      <div className={styles.adSlot} aria-hidden="true">
        {/* AD 728x90 leaderboard */}
      </div>
    </div>
  )
}
