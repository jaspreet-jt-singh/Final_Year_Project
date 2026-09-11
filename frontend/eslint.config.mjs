import nextVitals from 'eslint-config-next/core-web-vitals'

const config = [
  ...nextVitals,
  { ignores: ['.next/**', 'out/**', 'next-env.d.ts'] },
  { rules: {
    'react-hooks/set-state-in-effect': 'off',
    // User uploads use local blob/data URLs and are already resized before upload.
    '@next/next/no-img-element': 'off',
  } },
]

export default config
