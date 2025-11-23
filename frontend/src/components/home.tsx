import React, {useState, useRef, useEffect, type KeyboardEvent, type JSX} from 'react';
import {Send, User, Bot, Sun, Moon, Trash2, Copy, Check, Code, Image, X} from 'lucide-react';
import type {Message} from '../types/types.ts';
import CodePreview from './codePreview.tsx';

const Home: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState<string>('');
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [darkMode, setDarkMode] = useState<boolean>(true);
    const [copiedId, setCopiedId] = useState<string | null>(null);
    const [showCodePreview, setShowCodePreview] = useState<boolean>(true);
    const [previewCode, setPreviewCode] = useState<string>('');
    const [imagePreviews, setImagePreviews] = useState<string[]>([]);
    const [selectedImages, setSelectedImages] = useState<File[]>([]);
    const [isPreviewExpanded, setIsPreviewExpanded] = useState<boolean>(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Add these functions
    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files ? Array.from(e.target.files) : [];
        if (!files.length) return;

        setSelectedImages(files);

        Promise.all(
            files.map(
                (file) =>
                    new Promise<string>((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result as string);
                        reader.readAsDataURL(file);
                    })
            )
        ).then((previews) => setImagePreviews(previews));
    };

    const removeImage = (index?: number) => {
        if (index === undefined) {
            setSelectedImages([]);
            setImagePreviews([]);
        } else {
            const updatedFiles = selectedImages.filter((_, i) => i !== index);
            const updatedPreviews = imagePreviews.filter((_, i) => i !== index);
            setSelectedImages(updatedFiles);
            setImagePreviews(updatedPreviews);
        }
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const scrollToBottom = (): void => {
        messagesEndRef.current?.scrollIntoView({behavior: 'smooth'});
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (): Promise<void> => {
        if ((!input.trim() && selectedImages.length === 0) || isLoading) return;

        const prompt = input;
        const imageFiles = selectedImages;
        const imageDataList = imagePreviews;
        const imageData = imageDataList.length ? imageDataList[0] : undefined;

        // Create user message with image
        const userMessage: Message = {
            id: Date.now().toString(),
            content: prompt,
            role: 'user',
            timestamp: new Date(),
            image: imageData
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setSelectedImages([]);
        setImagePreviews([]);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }

        // Send to backend API
        try {
            setIsLoading(true);

            const formData = new FormData();
            formData.append('instructions', prompt);
            imageFiles.forEach((file) => formData.append('images', file));

            const response = await fetch('http://localhost:5378/api/v1/instructions/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const documentationUrl = response.headers.get('X-Documentation-URL');
            setPreviewCode(documentationUrl ?? '');
            const blob = await response.blob();

            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'template.zip'; // This will use the filename from Content-Disposition header
            document.body.appendChild(a);
            a.click();

            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                content: "Generated code",
                role: 'assistant',
                timestamp: new Date()
            };

            setMessages(prev => [...prev, aiMessage]);

        } catch (error) {
            console.error('❌ API call failed:', error);

            // Fallback to simulated response if API fails
            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                content: `API call failed: ${error instanceof Error ? error.message : 'Unknown error'}\n\nThis is a fallback simulated response.`,
                role: 'assistant',
                timestamp: new Date()
            };

            setMessages(prev => [...prev, aiMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const clearChat = (): void => {
        setMessages([]);
        setPreviewCode('// No code to preview yet. Send a message to see code here.');
    };

    const copyToClipboard = async (text: string, messageId: string): Promise<void> => {
        try {
            await navigator.clipboard.writeText(text);
            setCopiedId(messageId);
            setTimeout(() => setCopiedId(null), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    };

    const formatContent = (content: string): JSX.Element => {
        const parts = content.split(/(```[\s\S]*?```|`[^`]*`)/g);

        return (
            <>
                {parts.map((part, index) => {
                    if (part.startsWith('```') && part.endsWith('```')) {
                        const code = part.slice(3, -3);
                        const language = code.split('\n')[0].trim() || 'typescript';
                        const codeContent = code.replace(language, '').trim();

                        return (
                            <div key={index} className="relative my-4">
                                <div className="flex justify-between items-center bg-gray-700 px-4 py-2 rounded-t-lg">
                                    <span className="text-xs text-gray-300">{language}</span>
                                    <button
                                        onClick={() => copyToClipboard(codeContent, `code-${index}`)}
                                        className="text-gray-300 hover:text-white transition-colors"
                                    >
                                        {copiedId === `code-${index}` ? <Check size={14}/> : <Copy size={14}/>}
                                    </button>
                                </div>
                                <pre className="bg-gray-900 p-4 rounded-b-lg overflow-x-auto text-sm">
                                    <code>{codeContent}</code>
                                </pre>
                            </div>
                        );
                    } else if (part.startsWith('`') && part.endsWith('`')) {
                        return (
                            <code key={index} className="bg-gray-700 px-2 py-1 rounded text-sm">
                                {part.slice(1, -1)}
                            </code>
                        );
                    } else {
                        return (
                            <span key={index} className="whitespace-pre-wrap">
                                {part}
                            </span>
                        );
                    }
                })}
            </>
        );
    };

    return (
        <div className={`min-h-screen w-full transition-colors duration-200 ${
            darkMode
                ? 'bg-gradient-to-br from-slate-950 via-gray-900 to-slate-900 text-white'
                : 'bg-gradient-to-br from-slate-50 via-white to-indigo-50 text-gray-900'
        }`}>
            {isPreviewExpanded && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
                    <div className="h-[85vh] w-[min(1200px,95vw)]">
                        <CodePreview
                            initialCode={previewCode}
                            isExpanded
                            onExpandToggle={() => setIsPreviewExpanded(false)}
                        />
                    </div>
                </div>
            )}

            {/* Header */}
            <header className={`w-full border-b border-white/10 backdrop-blur ${
                darkMode ? 'bg-gray-900/80' : 'bg-white/80 shadow-sm'
            }`}>
                <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
                    <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-lg ${
                            darkMode ? 'bg-blue-600' : 'bg-blue-500'
                        }`}>
                            <Bot size={24} className="text-white"/>
                        </div>
                        <div>
                            <p className="text-xs uppercase tracking-wide text-gray-400">LauzHack Studio</p>
                            <h1 className="text-xl font-bold">AI React Builder</h1>
                        </div>
                    </div>

                    <div className="flex items-center space-x-3">
                        <button
                            onClick={() => setShowCodePreview(!showCodePreview)}
                            className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                                darkMode
                                    ? 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            } ${showCodePreview ? (darkMode ? 'ring-2 ring-blue-500/60' : 'ring-2 ring-blue-500/30') : ''}`}
                            title="Toggle code preview"
                        >
                            <div className="flex items-center gap-2">
                                <Code size={18}/>
                                <span>Preview</span>
                            </div>
                        </button>

                        <button
                            onClick={clearChat}
                            className={`rounded-full p-2 transition ${
                                darkMode
                                    ? 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                            title="Clear chat"
                        >
                            <Trash2 size={20}/>
                        </button>

                        <button
                            onClick={() => setDarkMode(!darkMode)}
                            className={`rounded-full p-2 transition ${
                                darkMode
                                    ? 'bg-gray-800 text-gray-200 hover:bg-gray-700'
                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                            title="Toggle theme"
                        >
                            {darkMode ? <Sun size={20}/> : <Moon size={20}/>}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="mx-auto flex w-full max-w-7xl gap-4 px-4 py-6 h-[calc(100vh-140px)]">
                {/* Chat Messages - Left Side */}
                <div className={`${showCodePreview ? 'w-1/2' : 'w-full'} transition-all duration-300 flex flex-col`}>
                    <div className={`flex flex-1 flex-col overflow-hidden rounded-2xl backdrop-blur shadow-2xl ${
                        darkMode ? 'bg-gray-900/70 ring-1 ring-white/5' : 'bg-white/80 ring-1 ring-gray-100'
                    }`}>
                        <main className="flex-1 overflow-y-auto px-6 py-6">
                            {messages.length === 0 ? (
                                <div className={`flex h-full flex-col items-center justify-center text-center ${
                                    darkMode ? 'text-gray-400' : 'text-gray-600'
                                }`}>
                                    <div className={`mb-4 rounded-full p-4 ${
                                        darkMode ? 'bg-gray-800' : 'bg-gray-100'
                                    }`}>
                                        <Bot size={32}/>
                                    </div>
                                    <h2 className="text-xl font-semibold mb-2">Start a brief or drop a sketch</h2>
                                    <p className="max-w-md">
                                        Describe the interface you need. I will orchestrate the build, generate code, and
                                        ship a ready-to-run preview.
                                    </p>
                                </div>
                            ) : (
                                <div className="space-y-6">
                                    {messages.map((message) => (
                                        <div
                                            key={message.id}
                                            className={`flex gap-4 ${
                                                message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
                                            }`}
                                        >
                                            <div
                                                className={`flex h-9 w-9 items-center justify-center rounded-full shadow ${
                                                    message.role === 'user'
                                                        ? (darkMode ? 'bg-blue-600' : 'bg-blue-500')
                                                        : (darkMode ? 'bg-gray-800' : 'bg-gray-200')
                                                }`}>
                                                {message.role === 'user' ? (
                                                    <User size={16} className="text-white"/>
                                                ) : (
                                                    <Bot size={16} className="text-white"/>
                                                )}
                                            </div>

                                            <div className={`flex-1 max-w-[80%] ${
                                                message.role === 'user' ? 'text-right' : 'text-left'
                                            }`}>
                                                <div className={`inline-block max-w-full px-4 py-3 rounded-2xl ${
                                                    message.role === 'user'
                                                        ? (darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white')
                                                        : (darkMode ? 'bg-gray-800/80 ring-1 ring-white/5' : 'bg-white shadow-sm ring-1 ring-gray-100')
                                                }`}>
                                                    {/* Display image if present */}
                                                    {message.image && (
                                                        <div className="mb-3">
                                                            <img
                                                                src={message.image}
                                                                alt="Uploaded"
                                                                className="max-w-xs max-h-48 rounded-lg"
                                                            />
                                                        </div>
                                                    )}
                                                    <div className="prose prose-invert max-w-none">
                                                        {formatContent(message.content)}
                                                    </div>
                                                </div>
                                                <div className={`mt-2 text-xs ${
                                                    darkMode ? 'text-gray-500' : 'text-gray-500'
                                                }`}>
                                                    {message.timestamp.toLocaleTimeString()}
                                                </div>
                                            </div>
                                        </div>
                                    ))}

                                    {isLoading && (
                                        <div className="flex gap-4">
                                            <div className={`flex h-9 w-9 items-center justify-center rounded-full ${
                                                darkMode ? 'bg-gray-800' : 'bg-gray-200'
                                            }`}>
                                                <Bot size={16} className="text-white"/>
                                            </div>
                                            <div className={`px-4 py-3 rounded-2xl ${
                                                darkMode ? 'bg-gray-800/80 ring-1 ring-white/5' : 'bg-white shadow-sm ring-1 ring-gray-100'
                                            }`}>
                                                <div className="flex space-x-2">
                                                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                                                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-100"></div>
                                                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400 delay-200"></div>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    <div ref={messagesEndRef}/>
                                </div>
                            )}
                        </main>

                        {/* Input Area */}
                        <footer className={`border-t flex-shrink-0 ${
                            darkMode ? 'bg-gray-900/70 border-gray-800/80' : 'bg-white/80 border-gray-200'
                        }`}>
                            <div className="p-4 space-y-3">
                                {/* Image Preview */}
                                {imagePreviews.length > 0 && (
                                    <div className="flex flex-wrap gap-3">
                                        {imagePreviews.map((preview, idx) => (
                                            <div
                                                key={idx}
                                                className="relative inline-block rounded-xl bg-black/5 p-1 dark:bg-white/5"
                                            >
                                                <img
                                                    src={preview}
                                                    alt={`Preview ${idx + 1}`}
                                                    className="h-20 w-20 object-cover rounded-lg"
                                                />
                                                <button
                                                    onClick={() => removeImage(idx)}
                                                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 shadow"
                                                    aria-label="Remove image"
                                                >
                                                    <X size={14}/>
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                <div className={`relative rounded-xl shadow-sm ring-1 transition-all ${
                                    darkMode
                                        ? 'bg-gray-800/80 ring-gray-700 focus-within:ring-blue-500'
                                        : 'bg-white ring-gray-200 focus-within:ring-blue-500'
                                }`}>
            <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Message AI assistant or upload an image..."
                className={`w-full px-4 py-3 pr-28 resize-none rounded-xl bg-transparent focus:outline-none ${
                    darkMode ? 'text-white' : 'text-gray-900'
                }`}
                rows={1}
                style={{minHeight: '56px', maxHeight: '200px'}}
            />

                                    {/* Image Upload Button */}
                                    <label
                                        className={`absolute bottom-2 right-14 flex h-10 w-10 cursor-pointer items-center justify-center rounded-lg text-white transition ${
                                            darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-800 hover:bg-gray-700'
                                        }`}>
                                        <Image size={16}/>
                                        <input
                                            ref={fileInputRef}
                                            type="file"
                                            accept="image/*"
                                            onChange={handleImageUpload}
                                            className="hidden"
                                        />
                                    </label>

                                    {/* Send Button */}
                                    <button
                                        onClick={handleSend}
                                        disabled={(!input.trim() && selectedImages.length === 0) || isLoading}
                                        className={`absolute bottom-2 right-2 flex h-10 w-10 items-center justify-center rounded-lg text-white transition ${
                                            (input.trim() || selectedImages.length > 0) && !isLoading
                                                ? 'bg-blue-600 hover:bg-blue-700'
                                                : 'bg-gray-400 cursor-not-allowed'
                                        }`}
                                    >
                                        <Send size={16}/>
                                    </button>
                                </div>

                                <div className={`text-xs text-center ${
                                    darkMode ? 'text-gray-500' : 'text-gray-500'
                                }`}>
                                    You can upload reference screenshots to guide the build
                                </div>
                            </div>
                        </footer>
                    </div>
                </div>

                {/* Code Preview - Right Side */}
                {showCodePreview && (
                    <div className="flex w-1/2 flex-col transition-all duration-300">
                        <div className="flex-1">
                            <CodePreview
                                initialCode={previewCode}
                                onExpandToggle={() => setIsPreviewExpanded(true)}
                            />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Home;
