import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const directory = path.join(root, 'frontend/out')
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
    const file = path.resolve(directory, `.${pathname === '/' ? '/index.html' : pathname}`)
    if (!file.startsWith(directory + path.sep)) { response.writeHead(403).end(); return }
    const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2' }
    response.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream')
    response.end(await readFile(file))
  } catch { response.writeHead(404).end() }
})
await new Promise((resolve, reject) => { server.once('error', reject); server.listen(4173, '127.0.0.1', resolve) })
try {
  for (const name of ['test_frontend.mjs', 'test_supported_foods_browser.mjs', 'test_journal_browser.mjs', 'test_health_browser.mjs']) {
    await new Promise((resolve, reject) => {
      const child = spawn(process.execPath, [path.join(root, 'scripts', name)], { cwd: root, stdio: 'inherit' })
      child.on('error', reject)
      child.on('exit', code => code === 0 ? resolve() : reject(new Error(`${name} failed (${code})`)))
    })
  }
} finally { server.close() }
