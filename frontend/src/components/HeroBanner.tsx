import Image from 'next/image'
import styles from './HeroBanner.module.css'

export default function HeroBanner() {
  return (
    <div className={styles.hero}>
      <Image
        src="/branding/banner-donde-juega-argentina.png"
        alt="Donde juega Argentina"
        width={876}
        height={104}
        priority
        className={styles.bannerImage}
      />
    </div>
  )
}
