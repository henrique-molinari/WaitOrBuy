// Gera src/design/tokens.css a partir de tokens.json. Rode: npm run tokens
import fs from 'node:fs'
const t = JSON.parse(fs.readFileSync('src/design/tokens.json', 'utf8'))
const [light, dark] = t.color.themes.map(x => x.id)
const val = (tok, th) => {
  const v = typeof tok.value === 'string' ? tok.value : (tok.value[th] ?? tok.value[light])
  return v.replace(/^\{(.+)\}$/, 'var(--$1)')
}
const colors = th => t.color.tokens.map(k => `  --${k.name}: ${val(k, th)};`).join('\n')
const scale = f => t[f].tokens.map(k => `  --${k.name}: ${k.value};`).join('\n')
const fam = Object.entries(t.type.families).map(([k, v]) => `  --font-${k}: ${v};`).join('\n')
const styles = t.type.groups.flatMap(g => g.styles.map(s =>
  `.t-${s.name}{font-family:var(--font-${g.family});font-size:${s.fontSize};line-height:${s.lineHeight};font-weight:${s.fontWeight};${s.letterSpacing ? `letter-spacing:${s.letterSpacing};` : ''}}`)).join('\n')
fs.writeFileSync('src/design/tokens.css', `/* WaitOrBuy — gerado de tokens.json (npm run tokens). Não edite. */
:root{\n${colors(light)}\n${fam}\n${scale('spacing')}\n${scale('radius')}\n  color-scheme: light;\n}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){\n${colors(dark)}\n  color-scheme: dark;\n}}
:root[data-theme="dark"]{\n${colors(dark)}\n  color-scheme: dark;\n}
${styles}
`)
