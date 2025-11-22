// CodePreview.tsx - Iframe approach with hardcoded URLs
import { useState, useEffect } from 'react'

interface CodePreviewProps {
    initialCode?: string;
}

const CodePreview: React.FC<CodePreviewProps> = ({ initialCode }) => {
    const [buildUrl, setBuildUrl] = useState<string>('')
    const [isBuilding, setIsBuilding] = useState(false)

    useEffect(() => {
        if (initialCode && initialCode.trim()) {
            // For testing, use a hardcoded URL instead of building
            simulateBuildProcess()
        } else {
            setBuildUrl('')
        }
    }, [initialCode])

    const simulateBuildProcess = () => {
        setIsBuilding(true)

        // Simulate build time
        setTimeout(() => {
            // Use one of these public React app URLs for testing:
            const testUrls = [
                'https://6922473187d6fcabc4f8e3e5--react-preview-1763854124.netlify.app',
            ]

            // Pick a random demo app URL
            const randomUrl = testUrls[Math.floor(Math.random() * testUrls.length)]
            setBuildUrl(randomUrl)
            setIsBuilding(false)
        }, 2000) // 2 second "build" simulation
    }

    return (
        <div className="h-full flex flex-col border border-gray-300 rounded-lg">
            <div className="bg-gray-100 px-4 py-2 border-b border-gray-300 font-bold">
                Live Preview {buildUrl && '(Demo App)'}
            </div>
            <div className="flex-1 min-h-[400px]">
                {isBuilding ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
                            <p className="mt-4">Building your React app...</p>
                        </div>
                    </div>
                ) : buildUrl ? (
                    <iframe
                        src={buildUrl}
                        className="w-full h-full border-0"
                        title="React App Preview"
                        sandbox="allow-scripts allow-same-origin" // Important for security
                    />
                ) : (
                    <div className="flex items-center justify-center h-full text-gray-500">
                        No project to preview. Send a message to generate a React app.
                    </div>
                )}
            </div>
        </div>
    )
}

export default CodePreview