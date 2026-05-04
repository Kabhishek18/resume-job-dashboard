'use strict'

const http = require('http')
const path = require('path')
const fs = require('fs')
const crypto = require('crypto')
const { spawn } = require('child_process')
const { app, BrowserWindow } = require('electron')
const serveHandler = require('serve-handler')

const API_PORT = 8000
const UI_PORT = 14208

let mainWindow = null
let backendChild = null
let uiServer = null

function isDevCli() {
  return process.argv.includes('--dev')
}

function ensureJwtSecret(userData) {
  const p = path.join(userData, '.jwt-secret')
  try {
    return fs.readFileSync(p, 'utf8').trim()
  } catch {
    const s = crypto.randomBytes(48).toString('hex')
    fs.writeFileSync(p, s, { encoding: 'utf8', mode: 0o600 })
    return s
  }
}

/** SQLAlchemy sqlite URL for an absolute file path. */
function databaseUrlForDbFile(dbFile) {
  fs.mkdirSync(path.dirname(dbFile), { recursive: true })
  const norm = path.resolve(dbFile).replace(/\\/g, '/')
  return `sqlite:///${norm}`
}

function waitForHttp(url, tries = 240) {
  // Cold PyInstaller startup (spaCy/torch/embeddings) can exceed ~60s on some machines.
  return new Promise((resolve) => {
    let n = 0
    const tick = () => {
      if (n >= tries) {
        resolve(false)
        return
      }
      n += 1
      const req = http.get(url, (res) => {
        res.resume()
        resolve(true)
      })
      req.on('error', () => setTimeout(tick, 400))
    }
    tick()
  })
}

function backendExecutablePath() {
  const ext = process.platform === 'win32' ? '.exe' : ''
  const dir = path.join(process.resourcesPath, 'backend', 'job-resume-api')
  return path.join(dir, `job-resume-api${ext}`)
}

function startBackend(workDir, uiOrigin) {
  const dbFile = path.join(workDir, 'data', 'app.db')
  const env = {
    ...process.env,
    APP_ENV: 'production',
    JOB_RESUME_DESKTOP: '1',
    JOB_RESUME_WORK_DIR: workDir,
    DATABASE_URL: databaseUrlForDbFile(dbFile),
    JWT_SECRET: ensureJwtSecret(workDir),
    FRONTEND_BASE_URL: uiOrigin,
    UVICORN_HOST: '127.0.0.1',
    PORT: String(API_PORT),
    LOG_LEVEL: 'info',
  }

  if (isDevCli()) {
    const root = path.resolve(__dirname, '..')
    const backendDir = path.join(root, 'backend-ai')
    const py = process.env.JOB_RESUME_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')
    backendChild = spawn(
      py,
      ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(API_PORT)],
      { cwd: backendDir, env },
    )
  } else {
    const exe = backendExecutablePath()
    if (!fs.existsSync(exe)) {
      throw new Error(
        `Packaged API binary not found: ${exe}. Build backend with: (cd backend-ai && pyinstaller job-resume-api.spec)`,
      )
    }
    const cwd = path.dirname(exe)
    backendChild = spawn(exe, [], { env, cwd })
  }

  backendChild.stderr?.on('data', (d) => process.stderr.write(d))
  backendChild.stdout?.on('data', (d) => process.stdout.write(d))
}

function startUiServer(staticDir) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      serveHandler(req, res, {
        public: staticDir,
        cleanUrls: false,
        trailingSlash: true,
      })
    })
    server.listen(UI_PORT, '127.0.0.1', () => resolve(server))
    server.on('error', reject)
  })
}

function staticUiDir() {
  if (isDevCli()) {
    return path.resolve(__dirname, '..', 'frontend', 'out')
  }
  return path.join(process.resourcesPath, 'frontend-out')
}

async function launch() {
  const workDir = app.getPath('userData')
  const uiOrigin = `http://127.0.0.1:${UI_PORT}`
  const staticDir = staticUiDir()

  if (!fs.existsSync(staticDir)) {
    throw new Error(
      `Static UI missing: ${staticDir}. Run: cd frontend && STATIC_EXPORT=true NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000 npm run build`,
    )
  }

  startBackend(workDir, uiOrigin)
  const ok = await waitForHttp(`http://127.0.0.1:${API_PORT}/docs`)
  if (!ok) {
    throw new Error('FastAPI did not start (timeout waiting for /docs). Check backend logs.')
  }

  uiServer = await startUiServer(staticDir)
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  })
  await mainWindow.loadURL(uiOrigin)
}

function shutdown() {
  if (uiServer) {
    try {
      uiServer.close()
    } catch {
      /* noop */
    }
    uiServer = null
  }
  if (backendChild && !backendChild.killed) {
    if (process.platform === 'win32') {
      try {
        spawn('taskkill', ['/pid', String(backendChild.pid), '/f', '/t'])
      } catch {
        backendChild.kill()
      }
    } else {
      backendChild.kill('SIGTERM')
    }
    backendChild = null
  }
}

app.whenReady().then(async () => {
  try {
    await launch()
  } catch (e) {
    console.error(e)
    app.quit()
  }
})

app.on('before-quit', () => shutdown())

app.on('window-all-closed', () => {
  shutdown()
  app.quit()
})
