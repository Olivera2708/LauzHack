import React, {useState, useRef, useEffect, type KeyboardEvent, type JSX} from 'react';
import { Send, User, Bot, Sun, Moon, Trash2, Copy, Check, Code, Image, X } from 'lucide-react';
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
    const [imagePreview, setImagePreview] = useState<string>('');
    const [selectedImage, setSelectedImage] = useState<File | null>(null);

    // Add these functions
    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedImage(file);
            const reader = new FileReader();
            reader.onload = (e) => {
                setImagePreview(e.target?.result as string);
            };
            reader.readAsDataURL(file);
        }
    };

    const removeImage = () => {
        setSelectedImage(null);
        setImagePreview('');
    };

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const scrollToBottom = (): void => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Extract code from messages and update preview
    useEffect(() => {
        console.log('Messages changed:', messages); // Debug log

        // Find the latest assistant message with code blocks
        const latestAssistantMessage = [...messages]
            .reverse()
            .find(message => message.role === 'assistant');

        if (latestAssistantMessage) {
            console.log('Latest assistant message:', latestAssistantMessage.content); // Debug log

            // Improved regex to capture code blocks
            const codeBlockRegex = /```(?:typescript|javascript|jsx|tsx)?\s*\n([\s\S]*?)```/;
            const codeMatch = latestAssistantMessage.content.match(codeBlockRegex);

            console.log('Code match:', codeMatch); // Debug log

            if (codeMatch && codeMatch[1]) {
                const extractedCode = codeMatch[1].trim();
                console.log('Extracted code:', extractedCode); // Debug log
                setPreviewCode(extractedCode);
            } else {
                console.log('No code block found or code block is empty');
                // Set a default message if no code is found
                setPreviewCode('// No code to preview yet. Send a message to see code here.');
            }
        } else {
            console.log('No assistant messages found');
            setPreviewCode('// No code to preview yet. Send a message to see code here.');
        }
    }, [messages]);

    const handleSend = async (): Promise<void> => {
        if ((!input.trim() && !selectedImage) || isLoading) return;

        // Create user message with image
        const userMessage: Message = {
            id: Date.now().toString(),
            content: input,
            role: 'user',
            timestamp: new Date(),
            image: selectedImage ? imagePreview : undefined
        };

        setMessages(prev => [...prev, userMessage]);

        // Send to backend API
        try {
            setIsLoading(true);

            const response = await fetch('http://localhost:8000/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: input,
                    image_data: selectedImage ? imagePreview : null
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('✅ Backend response:', data);

            // Create AI response based on backend reply
            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                content: `Backend says: "${data.message}"\n\nReceived at: ${data.backend_timestamp}\n\nData: ${JSON.stringify(data.received_data, null, 2)}`,
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
            setInput('');
            setSelectedImage(null);
            setImagePreview('');
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
                                        {copiedId === `code-${index}` ? <Check size={14} /> : <Copy size={14} />}
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
            darkMode ? 'bg-gray-900 text-white' : 'bg-gray-50 text-gray-900'
        }`}>
            {/* Header */}
            <header className={`border-b w-full ${
                darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'
            }`}>
                <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                        <div className={`p-2 rounded-lg ${
                            darkMode ? 'bg-blue-600' : 'bg-blue-500'
                        }`}>
                            <Bot size={24} className="text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold">AI Chat</h1>
                            <p className={`text-sm ${
                                darkMode ? 'text-gray-400' : 'text-gray-600'
                            }`}>
                                AI Assistant
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center space-x-4">
                        <button
                            onClick={() => setShowCodePreview(!showCodePreview)}
                            className={`p-2 rounded-lg transition-colors ${
                                darkMode
                                    ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-300'
                                    : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'
                            } ${showCodePreview ? (darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white') : ''}`}
                            title="Toggle code preview"
                        >
                            <Code size={20} />
                        </button>

                        <button
                            onClick={clearChat}
                            className={`p-2 rounded-lg transition-colors ${
                                darkMode
                                    ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-300'
                                    : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'
                            }`}
                            title="Clear chat"
                        >
                            <Trash2 size={20} />
                        </button>

                        <button
                            onClick={() => setDarkMode(!darkMode)}
                            className={`p-2 rounded-lg transition-colors ${
                                darkMode
                                    ? 'hover:bg-gray-700 text-gray-400 hover:text-gray-300'
                                    : 'hover:bg-gray-200 text-gray-600 hover:text-gray-800'
                            }`}
                            title="Toggle theme"
                        >
                            {darkMode ? <Sun size={20} /> : <Moon size={20} />}
                        </button>
                    </div>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex w-full max-w-7xl mx-auto h-[calc(100vh-140px)] ">
                {/* Chat Messages - Left Side */}
                <div className={`${showCodePreview ? 'w-1/2' : 'w-full'} transition-all duration-300 flex flex-col`}>
                    <main className="flex-1 overflow-y-auto px-4 py-6">
                        {messages.length === 0 ? (
                            <div className="text-center py-20">
                                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                                    darkMode ? 'bg-gray-800' : 'bg-gray-100'
                                }`}>
                                    <Bot size={32} className={darkMode ? 'text-blue-400' : 'text-blue-500'} />
                                </div>
                                <h2 className={`text-2xl font-bold mb-2 ${
                                    darkMode ? 'text-white' : 'text-gray-900'
                                }`}>
                                    How can I help you today?
                                </h2>
                                <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
                                    Ask me anything and I'll do my best to assist you.
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
                                        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                                            message.role === 'user'
                                                ? (darkMode ? 'bg-blue-600' : 'bg-blue-500')
                                                : (darkMode ? 'bg-gray-700' : 'bg-gray-300')
                                        }`}>
                                            {message.role === 'user' ? (
                                                <User size={16} className="text-white" />
                                            ) : (
                                                <Bot size={16} className="text-white" />
                                            )}
                                        </div>

                                        <div className={`flex-1 max-w-[80%] ${
                                            message.role === 'user' ? 'text-right' : 'text-left'
                                        }`}>
                                            <div className={`inline-block px-4 py-3 rounded-2xl ${
                                                message.role === 'user'
                                                    ? (darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white')
                                                    : (darkMode ? 'bg-gray-800' : 'bg-white border border-gray-200')
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
                                            <div className={`text-xs mt-2 ${
                                                darkMode ? 'text-gray-500' : 'text-gray-400'
                                            }`}>
                                                {message.timestamp.toLocaleTimeString()}
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                {isLoading && (
                                    <div className="flex gap-4">
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                            darkMode ? 'bg-gray-700' : 'bg-gray-300'
                                        }`}>
                                            <Bot size={16} className="text-white" />
                                        </div>
                                        <div className={`px-4 py-3 rounded-2xl ${
                                            darkMode ? 'bg-gray-800' : 'bg-white border border-gray-200'
                                        }`}>
                                            <div className="flex space-x-2">
                                                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce"></div>
                                                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </main>

                    {/* Input Area */}
                    {/* Input Area */}
                    <footer className={`border-t flex-shrink-0 ${
                        darkMode ? 'bg-gray-900 border-gray-700' : 'bg-gray-50 border-gray-200'
                    }`}>
                        <div className="p-4">
                            {/* Image Preview */}
                            {imagePreview && (
                                <div className="mb-3 relative inline-block">
                                    <img
                                        src={imagePreview}
                                        alt="Preview"
                                        className="h-20 w-20 object-cover rounded-lg border"
                                    />
                                    <button
                                        onClick={removeImage}
                                        className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            )}

                            <div className={`relative rounded-lg border ${
                                darkMode
                                    ? 'bg-gray-800 border-gray-600 focus-within:border-blue-500'
                                    : 'bg-white border-gray-300 focus-within:border-blue-500'
                            } transition-colors`}>
            <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Message AI assistant or upload an image..."
                className={`w-full px-4 py-3 pr-24 resize-none focus:outline-none ${
                    darkMode ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'
                }`}
                rows={1}
                style={{ minHeight: '56px', maxHeight: '200px' }}
            />

                                {/* Image Upload Button */}
                                <label className="absolute right-12 bottom-2 p-2 rounded-lg transition-colors cursor-pointer bg-gray-600 hover:bg-gray-700 text-white">
                                    <Image size={16} />
                                    <input
                                        type="file"
                                        accept="image/*"
                                        onChange={handleImageUpload}
                                        className="hidden"
                                    />
                                </label>

                                {/* Send Button */}
                                <button
                                    onClick={handleSend}
                                    disabled={(!input.trim() && !selectedImage) || isLoading}
                                    className={`absolute right-2 bottom-2 p-2 rounded-lg transition-colors ${
                                        (input.trim() || selectedImage) && !isLoading
                                            ? (darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600 text-white')
                                            : (darkMode ? 'bg-gray-700 text-gray-500' : 'bg-gray-300 text-gray-400')
                                    }`}
                                >
                                    <Send size={16} />
                                </button>
                            </div>

                            <div className={`text-xs text-center mt-2 ${
                                darkMode ? 'text-gray-500' : 'text-gray-400'
                            }`}>
                                You can upload images for analysis
                            </div>
                        </div>
                    </footer>
                </div>

                {/* Code Preview - Right Side */}
                {showCodePreview && (
                    <div className="w-1/2 border-l border-gray-700 p-4">
                        {/* Pass the extracted code to CodePreview */}
                        <CodePreview initialCode={previewCode} />
                    </div>
                )}
            </div>
        </div>
    );
};

export default Home;