import styles from './HeroBanner.module.css'

export default function HeroBanner() {
  return (
    <div className={styles.hero}>
      <svg className={styles.waves} viewBox="0 0 1200 120" preserveAspectRatio="none">
        <path d="M0 40 Q150 0 300 40 Q450 80 600 40 Q750 0 900 40 Q1050 80 1200 40 L1200 120 L0 120 Z"
          fill="#b8dff4" opacity="0.45"/>
        <path d="M0 60 Q150 20 300 60 Q450 100 600 60 Q750 20 900 60 Q1050 100 1200 60 L1200 120 L0 120 Z"
          fill="#74c0e8" opacity="0.3"/>
      </svg>
      <svg className={styles.mapas} viewBox="0 0 220 140" fill="none">
        <path d="M55 8 L75 6 L95 13 L112 10 L128 17 L138 13 L148 19 L143 34 L136 50 L128 66 L118 82 L106 98 L93 104 L78 96 L66 83 L55 68 L49 53 L45 38 Z"
          stroke="#1a5fa8" strokeWidth="1" fill="#74c0e8" fillOpacity=".25"/>
        <path d="M148 15 L163 12 L178 19 L186 15 L193 22 L190 35 L183 47 L173 59 L163 67 L153 62 L146 52 L143 39 Z"
          stroke="#1a5fa8" strokeWidth="0.8" fill="#74c0e8" fillOpacity=".2"/>
      </svg>
      <div className={styles.inner}>
        <h1 className={styles.title}>
          Donde juega <span className={styles.accent}>Argentina</span>
        </h1>
      </div>
    </div>
  )
}
