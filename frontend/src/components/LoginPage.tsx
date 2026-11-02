import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowRight,
  BookOpen,
  Eye,
  EyeOff,
  FileText,
  LockKeyhole,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { signIn } from '../lib/api'

interface LoginPageProps {
  onLogin: () => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setLoading(true)

    try {
      await signIn(username.trim(), password)
      onLogin()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to sign in.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-white">
      {/* Branding panel */}
      <section className="relative hidden w-[48%] flex-col justify-between overflow-hidden bg-[#112b28] p-12 text-white lg:flex xl:p-16">
        <div className="absolute -right-32 -top-24 h-[450px] w-[450px] rounded-full border border-teal-200/10" />
        <div className="absolute -right-14 top-20 h-[300px] w-[300px] rounded-full border border-teal-200/10" />
        <div className="absolute -bottom-48 -left-40 h-[500px] w-[500px] rounded-full border border-teal-200/10" />

        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-teal-300 to-emerald-500 text-[#102e29]">
            <BookOpen size={23} />
          </div>
          <div>
            <p className="text-xl font-bold tracking-tight">
              DocuMind <span className="text-teal-300">AI</span>
            </p>
            <p className="text-[9px] font-semibold tracking-[0.2em] text-teal-100/50">
              DOCUMENT INTELLIGENCE
            </p>
          </div>
        </div>

        <div className="relative max-w-lg py-12">
          <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-teal-300/20 bg-teal-300/10 px-3 py-2 text-[10px] font-semibold tracking-wide text-teal-200">
            <Sparkles size={13} />
            INTELLIGENT DOCUMENT WORKSPACE
          </div>

          <h1 className="text-4xl font-bold leading-[1.2] tracking-tight xl:text-5xl">
            Your documents.
            <br />
            Your knowledge.
            <br />
            <span className="text-teal-300">One conversation.</span>
          </h1>

          <p className="mt-6 max-w-md text-sm leading-7 text-slate-300/75">
            Bring your documents together, find the information that matters,
            and get answers grounded in your own knowledge base.
          </p>

          <div className="mt-12 space-y-5">
            {[
              {
                icon: FileText,
                title: 'One searchable knowledge base',
                description: 'Organize and retrieve information across documents.',
              },
              {
                icon: Sparkles,
                title: 'AI-powered answers',
                description: 'Ask questions in natural language and explore insights.',
              },
              {
                icon: ShieldCheck,
                title: 'Private by design',
                description: 'Authenticated access to your personal workspace.',
              },
            ].map((feature) => {
              const Icon = feature.icon

              return (
                <div key={feature.title} className="flex items-start gap-4">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/[0.07] text-teal-300">
                    <Icon size={17} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-white">
                      {feature.title}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-400">
                      {feature.description}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <p className="relative text-[10px] text-slate-500">
          © 2026 DocuMind AI · Intelligent document processing
        </p>
      </section>

      {/* Login form */}
      <section className="flex flex-1 items-center justify-center px-6 py-12 sm:px-12">
        <div className="w-full max-w-[400px]">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500 text-white">
              <BookOpen size={21} />
            </div>
            <p className="text-lg font-bold text-slate-900">
              DocuMind <span className="text-teal-600">AI</span>
            </p>
          </div>

          <div className="mb-8">
            <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
              <LockKeyhole size={22} />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Welcome back
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-500">
              Sign in to access your document intelligence workspace.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="username"
                className="mb-2 block text-xs font-semibold text-slate-700"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter your username"
                className="h-12 w-full rounded-lg border border-slate-200 bg-white px-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"
              />
            </div>

            <div>
              <div className="mb-2 flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-xs font-semibold text-slate-700"
                >
                  Password
                </label>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  className="h-12 w-full rounded-lg border border-slate-200 bg-white px-4 pr-12 text-sm outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10"
                />
                <button
                  type="button"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-xs leading-5 text-red-700"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#153a34] text-sm font-semibold text-white shadow-sm transition hover:bg-[#1d5147] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Signing in...' : 'Sign in to workspace'}
              {!loading && <ArrowRight size={16} />}
            </button>
          </form>

          <div className="mt-8 flex items-center justify-center gap-2 border-t border-slate-100 pt-6 text-[11px] text-slate-400">
            <ShieldCheck size={14} className="text-emerald-600" />
            Secured with Amazon Cognito authentication
          </div>

          <p className="mt-8 text-center text-[10px] text-slate-400">
            Access is restricted to authenticated workspace users.
          </p>
        </div>
      </section>
    </div>
  )
}
