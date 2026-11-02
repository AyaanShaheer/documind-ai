import { useEffect, useMemo, useRef, useState } from 'react'
import LoginPage from './components/LoginPage'
import { apiRequest, clearSession, getAccessToken } from './lib/api'
import type { ChangeEvent, DragEvent } from 'react'
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  BookOpen,
  CheckCircle2,
  Clock3,
  CloudUpload,
  Command,
  FileSpreadsheet,
  FileText,
  Filter,
  FolderOpen,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  MessageSquareText,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Bot,
  UserRound,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
  Zap,
} from 'lucide-react'

type Page = 'Overview' | 'Documents' | 'AI Assistant' | 'Activity' | 'Settings'
type DocumentStatus = 'Indexed' | 'Processing' | 'Failed'

type DocumentItem = {
  id: string | number
  name: string
  type: string
  size: string
  pages: number
  updated: string
  status: DocumentStatus
  chunkCount?: number
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: unknown[]
  model?: string
}


type ApiDocument = {
  document_id: string
  filename: string
  content_type?: string
  size_bytes?: number
  status?: string
  created_at?: string
  updated_at?: string
  chunk_count?: number
}

function normalizeDocumentStatus(status?: string): DocumentStatus {
  const value = (status || 'UPLOADING').toUpperCase()
  if (value === 'INDEXED') return 'Indexed'
  if (value === 'FAILED') return 'Failed'
  return 'Processing'
}

function formatDocumentBytes(bytes = 0): string {
  return bytes < 1048576
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1048576).toFixed(1)} MB`
}

function mapApiDocument(doc: ApiDocument): DocumentItem {
  return {
    id: doc.document_id,
    name: doc.filename,
    type: doc.filename.split('.').pop()?.toUpperCase() || 'FILE',
    size: formatDocumentBytes(Number(doc.size_bytes || 0)),
    pages: 0,
    updated: doc.updated_at || doc.created_at || '—',
    status: normalizeDocumentStatus(doc.status),
    chunkCount: Number(doc.chunk_count || 0),
  }
}


const navigation: {
  label: Page
  icon: typeof LayoutDashboard
}[] = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Documents', icon: FolderOpen },
  { label: 'AI Assistant', icon: MessageSquareText },
  { label: 'Activity', icon: Activity },
]

function StatusBadge({ status }: { status: DocumentStatus }) {
  const styles = {
    Indexed: 'bg-emerald-50 text-emerald-700',
    Processing: 'bg-amber-50 text-amber-700',
    Failed: 'bg-red-50 text-red-700',
  }

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${styles[status]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${
        status === 'Indexed' ? 'bg-emerald-500' :
        status === 'Processing' ? 'bg-amber-500' : 'bg-red-500'
      }`} />
      {status}
    </span>
  )
}

function DocumentIcon({ type }: { type: string }) {
  const Icon = type === 'XLSX' ? FileSpreadsheet : FileText

  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
      <Icon size={19} strokeWidth={1.8} />
    </div>
  )
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(getAccessToken()))
  const [activePage, setActivePage] = useState<Page>('Overview')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [documentsError, setDocumentsError] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatting, setIsChatting] = useState(false)
  const [chatError, setChatError] = useState('')

  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [dragging, setDragging] = useState(false)
  const [uploadMessage, setUploadMessage] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)


  useEffect(() => {
    if (!isAuthenticated) return

    let stopped = false
    let busy = false

    async function loadDocuments() {
      if (busy) return
      busy = true

      try {
        const response = await apiRequest('/api/v1/documents/')
        const data = await response.json().catch(() => ({}))

        if (response.status === 401) {
          clearSession()
          if (!stopped) setIsAuthenticated(false)
          return
        }

        if (!response.ok) {
          throw new Error(data.detail || 'Unable to load documents.')
        }

        if (!stopped) {
          const records: ApiDocument[] = data.documents || []
          setDocuments(records.map(mapApiDocument))
          setDocumentsError('')
        }
      } catch (error) {
        if (!stopped) {
          setDocumentsError(
            error instanceof Error ? error.message : 'Unable to load documents.',
          )
        }
      } finally {
        busy = false
        if (!stopped) setIsLoadingDocuments(false)
      }
    }

    void loadDocuments()
    const interval = window.setInterval(loadDocuments, 10000)

    return () => {
      stopped = true
      window.clearInterval(interval)
    }
  }, [isAuthenticated])

  const filteredDocuments = useMemo(() => {
    return documents.filter((document) => {
      const matchesSearch = document.name.toLowerCase().includes(query.toLowerCase())
      const matchesStatus = statusFilter === 'All' || document.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [documents, query, statusFilter])

  function formatFileSize(bytes: number): string {
    if (bytes < 1024 * 1024) {
      return `${Math.max(1, Math.round(bytes / 1024))} KB`
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0 || isUploading) return

    const selectedFiles = Array.from(files)

    async function uploadSelectedFiles() {
      setIsUploading(true)
      setUploadMessage('')

      let uploadedCount = 0

      try {
        for (const file of selectedFiles) {
          const formData = new FormData()
          formData.append('file', file)

          const response = await apiRequest(
            '/api/v1/documents/upload',
            {
              method: 'POST',
              body: formData,
            },
          )

          const data = await response.json().catch(() => ({}))

          if (response.status === 401) {
            clearSession()
            setIsAuthenticated(false)
            throw new Error('Your session expired. Please sign in again.')
          }

          if (!response.ok) {
            throw new Error(
              data.detail || `Upload failed for ${file.name}.`,
            )
          }

          const extension = file.name.split('.').pop()?.toUpperCase() || 'FILE'

          const uploadedDocument: DocumentItem = {
            id: data.document_id || `${Date.now()}-${file.name}`,
            name: data.filename || file.name,
            type: extension,
            size: formatFileSize(Number(data.size_bytes ?? file.size)),
            pages: 0,
            updated: 'Just now',
            status: 'Processing',
          }

          setDocuments((previous) => [
            uploadedDocument,
            ...previous,
          ])

          uploadedCount += 1
        }

        setUploadMessage(
          `${uploadedCount} document${uploadedCount === 1 ? '' : 's'} uploaded successfully. Processing has been queued.`,
        )
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Upload failed.'

        setUploadMessage(
          uploadedCount > 0
            ? `${uploadedCount} file(s) uploaded. ${message}`
            : message,
        )
      } finally {
        setIsUploading(false)
      }
    }

    void uploadSelectedFiles()
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    handleFiles(event.target.files)
    event.target.value = ''
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    handleFiles(event.dataTransfer.files)
  }

  const isDocumentsPage = activePage === 'Documents'

  async function sendChatMessage(questionOverride?: string) {
    const question = (questionOverride ?? chatInput).trim()

    if (!question || isChatting) return

    setChatError('')
    setChatInput('')

    setChatMessages((previous) => [
      ...previous,
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: question,
      },
    ])

    setIsChatting(true)

    try {
      const response = await apiRequest('/api/v1/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          top_k: 5,
        }),
      })

      const data = await response.json().catch(() => ({}))

      if (response.status === 401) {
        clearSession()
        setIsAuthenticated(false)
        return
      }

      if (!response.ok) {
        throw new Error(data.detail || 'The AI request failed.')
      }

      const sources = Array.isArray(data.sources)
        ? data.sources
        : Array.isArray(data.retrieved_chunks)
          ? data.retrieved_chunks
          : []

      setChatMessages((previous) => [
        ...previous,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: String(data.answer ?? 'The assistant returned no answer.'),
          sources,
          model: typeof data.model === 'string' ? data.model : undefined,
        },
      ])
    } catch (error) {
      setChatError(
        error instanceof Error ? error.message : 'Unable to contact the AI assistant.',
      )
    } finally {
      setIsChatting(false)
    }
  }

  function handleLogout() {
    clearSession()
    setIsAuthenticated(false)
    setActivePage('Overview')
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-[#f7f8fa] text-slate-900">
      {/* Mobile overlay */}
      {mobileMenu && (
        <button
          aria-label="Close menu"
          onClick={() => setMobileMenu(false)}
          className="fixed inset-0 z-30 bg-slate-950/40 lg:hidden"
        />
      )}

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[258px] flex-col bg-[#111827] text-slate-300 transition-transform duration-200 lg:translate-x-0 ${
        mobileMenu ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex h-[76px] items-center justify-between border-b border-white/[0.07] px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-teal-300 to-emerald-500 text-slate-950">
              <BookOpen size={20} strokeWidth={2.3} />
            </div>
            <div>
              <p className="text-[17px] font-bold tracking-tight text-white">DocuMind<span className="text-teal-300"> AI</span></p>
              <p className="text-[10px] font-medium tracking-[0.19em] text-slate-500">DOCUMENT INTELLIGENCE</p>
            </div>
          </div>
          <button onClick={() => setMobileMenu(false)} className="lg:hidden">
            <X size={19} />
          </button>
        </div>

        <div className="px-4 pt-7">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Workspace
          </p>

          <div className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const active = activePage === item.label

              return (
                <button
                  key={item.label}
                  onClick={() => {
                    setActivePage(item.label)
                    setMobileMenu(false)
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] font-medium transition ${
                    active
                      ? 'bg-teal-400/10 text-teal-300'
                      : 'text-slate-400 hover:bg-white/[0.05] hover:text-white'
                  }`}
                >
                  <Icon size={18} strokeWidth={1.8} />
                  {item.label}
                  {item.label === 'Documents' && (
                    <span className="ml-auto rounded-md bg-white/[0.07] px-2 py-0.5 text-[10px] text-slate-400">
                      {documents.length}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        <div className="mt-8 px-4">
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
            Preferences
          </p>
          <button
            onClick={() => setActivePage('Settings')}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium transition ${
              activePage === 'Settings'
                ? 'bg-teal-400/10 text-teal-300'
                : 'text-slate-400 hover:bg-white/[0.05] hover:text-white'
            }`}
          >
            <Settings2 size={18} strokeWidth={1.8} />
            Settings
          </button>
          <button className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-[13px] font-medium text-slate-400 hover:bg-white/[0.05] hover:text-white">
            <LockKeyhole size={18} strokeWidth={1.8} />
            Security
          </button>
        </div>

        <div className="mt-auto px-4 pb-5">
          <div className="rounded-xl border border-white/[0.08] bg-white/[0.035] p-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-400/10 text-teal-300">
                <Zap size={16} />
              </div>
              <span className="text-xs font-semibold text-white">AI-powered workspace</span>
            </div>
            <p className="text-[11px] leading-5 text-slate-400">
              Turn your documents into searchable knowledge with intelligent retrieval.
            </p>
            <div className="mt-4 flex items-center gap-2 border-t border-white/[0.07] pt-3">
              <ShieldCheck size={14} className="text-emerald-400" />
              <span className="text-[10px] text-slate-500">Secure workspace architecture</span>
            </div>
          </div>

          <div className="mt-5 flex items-center gap-3 border-t border-white/[0.07] pt-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-teal-300 to-emerald-600 text-xs font-bold text-slate-950">
              U
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">Workspace User</p>
              <p className="text-[10px] text-slate-500">Personal workspace</p>
            </div>
            <MoreHorizontal size={18} className="text-slate-500" />
          </div>
        </div>
      </aside>

      {/* Main layout */}
      <div className="min-h-screen lg:pl-[258px]">
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex h-[76px] items-center justify-between border-b border-slate-200/80 bg-white/90 px-5 backdrop-blur-xl sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenu(true)}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
            >
              <Command size={18} />
            </button>
            <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex">
              Workspace <span>/</span>
              <span className="font-semibold text-slate-700">{activePage}</span>
            </div>
            <h2 className="text-sm font-semibold text-slate-800 sm:hidden">{activePage}</h2>
          </div>

          <div className="flex items-center gap-3 sm:gap-5">
            <div className="hidden h-9 w-[230px] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 md:flex">
              <Search size={15} className="text-slate-400" />
              <input
                className="w-full bg-transparent text-xs outline-none placeholder:text-slate-400"
                placeholder="Search your workspace..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] text-slate-400">⌘ K</kbd>
            </div>
            <button className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100">
              <Bell size={18} strokeWidth={1.7} />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-teal-500 ring-2 ring-white" />
            </button>
            <button
              onClick={handleLogout}
              title="Sign out"
              aria-label="Sign out"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-teal-100 bg-teal-50 text-teal-700 transition hover:bg-red-50 hover:text-red-600"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          {/* Preview notice */}
          <div className="mb-7 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-indigo-100 bg-indigo-50/70 px-4 py-2.5">
            <div className="flex items-center gap-2 text-xs text-indigo-800">
              <Sparkles size={14} />
              <span className="font-semibold">Live workspace</span>
              <span className="hidden text-indigo-600 sm:inline">Showing documents from your authenticated workspace.</span>
            </div>
            <span className="rounded-md bg-white px-2 py-1 text-[9px] font-bold tracking-wider text-indigo-600">LIVE</span>
          </div>

          {/* Page heading */}
          <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <p className="mb-2 flex items-center gap-2 text-xs font-semibold text-teal-700">
                <span className="h-1.5 w-1.5 rounded-full bg-teal-500" />
                YOUR KNOWLEDGE WORKSPACE
              </p>
              <h1 className="text-[27px] font-bold tracking-tight text-slate-900 sm:text-[32px]">
                {isDocumentsPage ? 'Document library' :
                 activePage === 'AI Assistant' ? 'AI Assistant' :
                 activePage === 'Activity' ? 'Activity' :
                 activePage === 'Settings' ? 'Workspace settings' :
                 'Good to see you'}
              </h1>
              <p className="mt-2 text-sm text-slate-500">
                {isDocumentsPage
                  ? 'Manage, organize and explore your knowledge base.'
                  : activePage === 'AI Assistant'
                  ? 'Ask questions and discover insights across your documents.'
                  : activePage === 'Activity'
                  ? 'Keep track of document processing and workspace events.'
                  : activePage === 'Settings'
                  ? 'Manage your workspace preferences and connections.'
                  : 'Your documents, intelligently organized and ready to explore.'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => inputRef.current?.click()}
                disabled={isUploading}
                className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#132d2a] px-4 text-xs font-semibold text-white shadow-sm transition hover:bg-[#1c4840] disabled:cursor-wait disabled:opacity-60"
              >
                <Plus size={16} />
                {isUploading ? 'Uploading...' : 'Upload document'}
              </button>
              <input
                ref={inputRef}
                type="file"
                multiple
                accept=".pdf,.txt,.doc,.docx,.csv"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>
          </div>

          {/* Overview dashboard */}
          {activePage === 'Overview' && (
            <>
              {documentsError && (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                  {documentsError}
                </div>
              )}

              {isLoadingDocuments && (
                <p className="mb-4 text-xs text-slate-400">Loading your documents...</p>
              )}

              {/* KPI cards */}
              <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  { label: 'Total documents', value: String(documents.length), detail: 'In your workspace', icon: FileText, color: 'text-indigo-600', bg: 'bg-indigo-50' },
                  { label: 'Successfully indexed', value: String(documents.filter(d => d.status === 'Indexed').length), detail: 'Ready for retrieval', icon: CheckCircle2, color: 'text-emerald-600', bg: 'bg-emerald-50' },
                  { label: 'Processing', value: String(documents.filter(d => d.status === 'Processing').length), detail: 'Currently in queue', icon: Clock3, color: 'text-amber-600', bg: 'bg-amber-50' },
                  { label: 'Knowledge chunks', value: documents.reduce((sum, d) => sum + (d.chunkCount || 0), 0).toLocaleString(), detail: 'Across your documents', icon: LayersIcon, color: 'text-violet-600', bg: 'bg-violet-50' },
                ].map((stat) => {
                  const Icon = stat.icon
                  return (
                    <div key={stat.label} className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,0.025)]">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-500">{stat.label}</span>
                        <span className={`flex h-9 w-9 items-center justify-center rounded-lg ${stat.bg} ${stat.color}`}>
                          <Icon size={18} strokeWidth={1.8} />
                        </span>
                      </div>
                      <div className="mt-4 flex items-end justify-between">
                        <span className="text-[27px] font-bold tracking-tight text-slate-900">{stat.value}</span>
                        <span className="mb-1 text-[10px] font-medium text-slate-400">{stat.detail}</span>
                      </div>
                    </div>
                  )
                })}
              </div>

              <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(280px,0.85fr)]">
                {/* Recent documents */}
                <section className="min-w-0 overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-[0_2px_8px_rgba(15,23,42,0.025)]">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-5 sm:px-6">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Recent documents</h3>
                      <p className="mt-1 text-xs text-slate-400">Your latest knowledge uploads</p>
                    </div>
                    <button
                      onClick={() => setActivePage('Documents')}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 hover:text-teal-900"
                    >
                      View all <ArrowRight size={14} />
                    </button>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[600px] text-left">
                      <thead className="bg-slate-50/80">
                        <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                          <th className="px-6 py-3">Document</th>
                          <th className="px-4 py-3">Last updated</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {documents.slice(0, 4).map((doc) => (
                          <tr key={doc.id} className="transition hover:bg-slate-50/70">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <DocumentIcon type={doc.type} />
                                <div className="min-w-0">
                                  <p className="max-w-[240px] truncate text-xs font-semibold text-slate-800">{doc.name}</p>
                                  <p className="mt-1 text-[10px] text-slate-400">{doc.type} · {doc.size}</p>
                                </div>
                              </div>
                            </td>
                            <td className="whitespace-nowrap px-4 py-4 text-[11px] text-slate-500">{doc.updated}</td>
                            <td className="px-4 py-4"><StatusBadge status={doc.status} /></td>
                            <td className="px-4 py-4 text-right">
                              <button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700">
                                <MoreHorizontal size={17} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                {/* Upload panel */}
                <section className="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_2px_8px_rgba(15,23,42,0.025)] sm:p-6">
                  <div className="mb-5 flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Add knowledge</h3>
                      <p className="mt-1 text-xs text-slate-400">Upload documents to your workspace</p>
                    </div>
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
                      <CloudUpload size={19} />
                    </div>
                  </div>

                  <div
                    onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={handleDrop}
                    onClick={() => inputRef.current?.click()}
                    className={`flex min-h-[190px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-4 py-6 text-center transition ${
                      dragging
                        ? 'border-teal-500 bg-teal-50'
                        : 'border-slate-300 bg-slate-50/70 hover:border-teal-400 hover:bg-teal-50/40'
                    }`}
                  >
                    <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white text-teal-700 shadow-sm">
                      <Upload size={21} />
                    </div>
                    <p className="text-xs font-semibold text-slate-800">Drop your files here</p>
                    <p className="mt-1 text-[11px] text-slate-400">or click to browse your computer</p>
                    <p className="mt-4 text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                      PDF · DOCX · TXT · CSV
                    </p>
                  </div>

                  {uploadMessage && (
                    <div className="mt-3 flex items-start justify-between gap-2 rounded-lg bg-teal-50 p-3 text-[11px] text-teal-800">
                      <span>{uploadMessage}</span>
                      <button onClick={() => setUploadMessage('')}><X size={14} /></button>
                    </div>
                  )}

                  <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                    <span className="text-[10px] text-slate-400">Maximum file size: 20 MB</span>
                    <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-700">
                      <ShieldCheck size={12} /> Secure upload
                    </span>
                  </div>
                </section>
              </div>

              {/* AI feature card */}
              <section className="relative mt-6 overflow-hidden rounded-xl bg-[#142e2b] p-6 text-white sm:p-8">
                <div className="pointer-events-none absolute -right-12 -top-24 h-72 w-72 rounded-full border border-teal-300/10" />
                <div className="pointer-events-none absolute -right-2 -top-10 h-52 w-52 rounded-full border border-teal-300/10" />
                <div className="relative flex flex-col justify-between gap-6 md:flex-row md:items-center">
                  <div className="max-w-xl">
                    <div className="mb-3 flex items-center gap-2 text-teal-300">
                      <Sparkles size={16} />
                      <span className="text-[10px] font-bold uppercase tracking-[0.18em]">Intelligence at work</span>
                    </div>
                    <h3 className="text-xl font-bold tracking-tight sm:text-2xl">Your documents have answers.</h3>
                    <p className="mt-2 max-w-lg text-xs leading-6 text-slate-300">
                      Ask natural-language questions, retrieve relevant passages, and discover insights across your knowledge base.
                    </p>
                  </div>
                  <button
                    onClick={() => setActivePage('AI Assistant')}
                    className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-teal-300 px-5 text-xs font-bold text-[#102e29] transition hover:bg-teal-200"
                  >
                    Explore AI Assistant <ArrowUpRight size={16} />
                  </button>
                </div>
              </section>
            </>
          )}

          {/* Documents page */}
          {activePage === 'Documents' && (
            <section className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-sm">
              <div className="flex flex-col justify-between gap-4 border-b border-slate-100 p-5 sm:flex-row sm:items-center sm:px-6">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">All documents</h3>
                  <p className="mt-1 text-xs text-slate-400">{filteredDocuments.length} documents displayed</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex h-9 min-w-[190px] items-center gap-2 rounded-lg border border-slate-200 px-3">
                    <Search size={14} className="text-slate-400" />
                    <input
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Search documents..."
                      className="w-full text-xs outline-none placeholder:text-slate-400"
                    />
                  </div>
                  <div className="flex h-9 items-center gap-2 rounded-lg border border-slate-200 px-3">
                    <Filter size={14} className="text-slate-400" />
                    <select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      className="bg-transparent text-xs text-slate-600 outline-none"
                    >
                      <option>All</option>
                      <option>Indexed</option>
                      <option>Processing</option>
                      <option>Failed</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[650px] text-left">
                  <thead className="bg-slate-50">
                    <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      <th className="px-6 py-4">Name</th>
                      <th className="px-4 py-4">Size</th>
                      <th className="px-4 py-4">Pages</th>
                      <th className="px-4 py-4">Updated</th>
                      <th className="px-4 py-4">Status</th>
                      <th className="px-4 py-4"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-50/70">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <DocumentIcon type={doc.type} />
                            <span className="text-xs font-semibold text-slate-800">{doc.name}</span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-xs text-slate-500">{doc.size}</td>
                        <td className="px-4 py-4 text-xs text-slate-500">{doc.pages > 0 ? doc.pages : '—'}</td>
                        <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-500">{doc.updated}</td>
                        <td className="px-4 py-4"><StatusBadge status={doc.status} /></td>
                        <td className="px-4 py-4"><button className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"><MoreHorizontal size={17} /></button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredDocuments.length === 0 && (
                <div className="py-14 text-center">
                  <FolderOpen size={28} className="mx-auto text-slate-300" />
                  <p className="mt-3 text-sm font-semibold text-slate-700">No documents found</p>
                  <p className="mt-1 text-xs text-slate-400">Try adjusting your search or filter.</p>
                </div>
              )}
            </section>
          )}

          {/* AI Assistant page */}
          {activePage === 'AI Assistant' && (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
              <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
                <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
                      <Sparkles size={19} />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Document AI Assistant</h3>
                      <p className="mt-1 text-[11px] text-slate-400">
                        Answers grounded in your documents
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setChatMessages([])
                      setChatError('')
                    }}
                    className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-[11px] font-semibold text-slate-600 hover:bg-slate-50"
                  >
                    <RefreshCw size={13} /> New chat
                  </button>
                </div>

                <div className="flex max-h-[560px] min-h-[390px] flex-col gap-5 overflow-y-auto bg-slate-50/60 p-5 sm:p-6">
                  {chatMessages.length === 0 && (
                    <div className="m-auto max-w-lg py-8 text-center">
                      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-teal-50 text-teal-700">
                        <Bot size={27} />
                      </div>
                      <h3 className="mt-5 text-lg font-bold text-slate-900">
                        Ask your documents anything
                      </h3>
                      <p className="mt-2 text-xs leading-6 text-slate-500">
                        Ask a question and DocuMind will retrieve relevant passages
                        from your indexed documents.
                      </p>

                      <div className="mt-7 grid gap-2 text-left sm:grid-cols-2">
                        {[
                          'Summarize my uploaded documents',
                          'What are the key technical requirements?',
                          'Find information about infrastructure',
                          'What are the main risks mentioned?',
                        ].map((prompt) => (
                          <button
                            key={prompt}
                            disabled={isChatting}
                            onClick={() => void sendChatMessage(prompt)}
                            className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-3 text-left text-[11px] font-medium text-slate-700 transition hover:border-teal-300 hover:bg-teal-50/50 disabled:opacity-50"
                          >
                            {prompt}
                            <ArrowUpRight size={14} className="shrink-0 text-teal-700" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex gap-3 ${
                        message.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {message.role === 'assistant' && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-100 text-teal-800">
                          <Bot size={17} />
                        </div>
                      )}

                      <div
                        className={`max-w-[88%] rounded-xl p-4 ${
                          message.role === 'user'
                            ? 'bg-[#153a34] text-white'
                            : 'border border-slate-200 bg-white text-slate-800'
                        }`}
                      >
                        <p className="whitespace-pre-wrap text-xs leading-6">
                          {message.content}
                        </p>

                        {message.role === 'assistant' && message.model && (
                          <p className="mt-3 text-[9px] text-slate-400">
                            Generated by {message.model}
                          </p>
                        )}

                        {message.role === 'assistant' &&
                          (message.sources?.length ?? 0) > 0 && (
                            <div className="mt-4 border-t border-slate-100 pt-3">
                              <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                                Retrieved sources
                              </p>

                              <div className="space-y-2">
                                {message.sources!.map((source, index) => {
                                  const item =
                                    typeof source === 'object' && source !== null
                                      ? source as Record<string, unknown>
                                      : { filename: String(source) }

                                  const filename = String(
                                    item.filename ??
                                    item.document_name ??
                                    item.source ??
                                    'Document source',
                                  )

                                  const page = item.page_number ?? item.page

                                  return (
                                    <div
                                      key={index}
                                      className="flex items-center gap-2 rounded-lg bg-slate-50 p-2"
                                    >
                                      <FileText size={14} className="shrink-0 text-teal-700" />
                                      <span className="min-w-0 truncate text-[10px] font-medium text-slate-600">
                                        {filename}
                                        {page != null ? ` · Page ${page}` : ''}
                                      </span>
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}
                      </div>

                      {message.role === 'user' && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-slate-700">
                          <UserRound size={16} />
                        </div>
                      )}
                    </div>
                  ))}

                  {isChatting && (
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-800">
                        <Bot size={17} />
                      </div>
                      Retrieving documents and generating an answer...
                    </div>
                  )}
                </div>

                {chatError && (
                  <div role="alert" className="mx-5 mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                    {chatError}
                  </div>
                )}

                <form
                  onSubmit={(event) => {
                    event.preventDefault()
                    void sendChatMessage()
                  }}
                  className="border-t border-slate-100 bg-white p-4 sm:p-5"
                >
                  <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-2 focus-within:border-teal-400 focus-within:ring-4 focus-within:ring-teal-500/10">
                    <input
                      value={chatInput}
                      onChange={(event) => setChatInput(event.target.value)}
                      placeholder="Ask a question about your documents..."
                      disabled={isChatting}
                      className="min-w-0 flex-1 bg-transparent px-2 py-2 text-xs outline-none placeholder:text-slate-400"
                    />
                    <button
                      type="submit"
                      disabled={!chatInput.trim() || isChatting}
                      aria-label="Send message"
                      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#153a34] text-white transition hover:bg-[#1d5147] disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      <Send size={16} />
                    </button>
                  </div>
                  <p className="mt-2 text-[9px] text-slate-400">
                    Answers are generated using retrieved content from your own indexed documents.
                  </p>
                </form>
              </section>

              <aside className="space-y-4">
                <section className="rounded-xl border border-slate-200 bg-white p-5">
                  <h3 className="text-xs font-bold text-slate-900">Your knowledge base</h3>
                  <div className="mt-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Documents</span>
                      <strong className="text-sm text-slate-900">{documents.length}</strong>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Indexed</span>
                      <strong className="text-sm text-emerald-700">
                        {documents.filter((doc) => doc.status === 'Indexed').length}
                      </strong>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500">Knowledge chunks</span>
                      <strong className="text-sm text-slate-900">
                        {documents.reduce((sum, doc) => sum + (doc.chunkCount ?? 0), 0).toLocaleString()}
                      </strong>
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-teal-100 bg-teal-50/60 p-5">
                  <div className="flex items-center gap-2 text-teal-800">
                    <ShieldCheck size={16} />
                    <h3 className="text-xs font-bold">Private retrieval</h3>
                  </div>
                  <p className="mt-3 text-[11px] leading-5 text-teal-900/70">
                    Your questions use the authenticated workspace identity. Retrieval is scoped to your own documents.
                  </p>
                </section>
              </aside>
            </div>
          )}

          {/* Activity and settings placeholders */}
          {(activePage === 'Activity' || activePage === 'Settings') && (
            <section className="rounded-xl border border-slate-200 bg-white px-6 py-16 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-slate-100 text-slate-500">
                {activePage === 'Activity' ? <Activity size={24} /> : <Settings2 size={24} />}
              </div>
              <h2 className="mt-5 text-lg font-bold text-slate-900">{activePage} workspace</h2>
              <p className="mx-auto mt-2 max-w-md text-xs leading-6 text-slate-500">
                This section is part of the frontend foundation. We'll connect it to real processing events and user preferences as the API integration develops.
              </p>
            </section>
          )}

          <footer className="mt-10 flex flex-col justify-between gap-2 border-t border-slate-200/80 py-5 text-[10px] text-slate-400 sm:flex-row sm:items-center">
            <span>© 2026 DocuMind AI. Intelligent document processing.</span>
            <span className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Live workspace environment
            </span>
          </footer>
        </main>
      </div>
    </div>
  )
}

// Small wrapper so the KPI icon is consistent with the other Lucide icons.
function LayersIcon({ size = 18 }: { size?: number }) {
  return <BookOpen size={size} strokeWidth={1.8} />
}

export default App
