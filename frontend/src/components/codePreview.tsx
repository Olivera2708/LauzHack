import { useEffect, useState } from 'react'
import { Maximize2, Minimize2, RotateCcw } from 'lucide-react'

interface CodePreviewProps {
    initialCode?: string
    isExpanded?: boolean
    onExpandToggle?: () => void
}

const CodePreview: React.FC<CodePreviewProps> = ({ initialCode, isExpanded = false, onExpandToggle }) => {
    const [buildUrl, setBuildUrl] = useState<string>('')
    const [isBuilding, setIsBuilding] = useState(false)
    const [lastBuiltAt, setLastBuiltAt] = useState<string>('')

    const simulateBuildProcess = () => {
        if (!initialCode || !initialCode.trim()) {
            setBuildUrl('')
            return
        }

        setIsBuilding(true)

        // Simulate build time
        setTimeout(() => {
            setBuildUrl(initialCode)
            setIsBuilding(false)
            setLastBuiltAt(new Date().toLocaleTimeString())
        }, 1200)
    }

    useEffect(() => {
        if (initialCode && initialCode.trim()) {
            simulateBuildProcess()
        } else {
            setBuildUrl('')
            setLastBuiltAt('')
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialCode])

    const headerDescription = lastBuiltAt
        ? `Updated at ${lastBuiltAt}`
        : 'Waiting for a build link'

    return (
        <div
            className={`flex h-full flex-col rounded-2xl bg-white/90 p-4 shadow-2xl backdrop-blur-lg transition-all dark:bg-gray-900/90 ${
                isExpanded ? 'ring-2 ring-indigo-500/30' : ''
            }`}
        >
            <div className="flex items-center justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">Live Preview</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{headerDescription}</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={simulateBuildProcess}
                        disabled={!initialCode || isBuilding}
                        className="inline-flex h-9 items-center gap-2 rounded-lg bg-indigo-600 px-3 text-sm font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-400"
                    >
                        <RotateCcw className="h-4 w-4" />
                        Refresh
                    </button>
                    {onExpandToggle && (
                        <button
                            onClick={onExpandToggle}
                            className="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gray-100 text-gray-700 transition hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
                            aria-label={isExpanded ? 'Collapse preview' : 'Expand preview'}
                        >
                            {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                        </button>
                    )}
                </div>
            </div>

            <div className="relative mt-4 flex-1 rounded-xl bg-gradient-to-br from-slate-200 via-white to-slate-100 p-[1px] dark:from-gray-800 dark:via-gray-900 dark:to-gray-800">
                <div className="preview-scroll relative h-full w-full overflow-y-auto rounded-[14px] bg-white shadow-inner dark:bg-gray-950">
                    {isBuilding ? (
                        <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-sm text-gray-500 dark:text-gray-300">
                            <div className="h-12 w-12 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-600" />
                            <p>Building your React app...</p>
                        </div>
                    ) : buildUrl ? (
                        <iframe
                            src={buildUrl}
                            className="h-full w-full rounded-[12px] border-0"
                            title="React App Preview"
                            sandbox="allow-scripts allow-same-origin"
                        />
                    ) : (
                        <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-gray-500 dark:text-gray-300">
                            <p>No project to preview yet.</p>
                            <p className="text-xs text-gray-400 dark:text-gray-500">
                                Ask the assistant to generate a React app to see it live.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default CodePreview
