// types.ts
export interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant';
    timestamp: Date;
    image: string | undefined;
}

export interface ChatState {
    messages: Message[];
    input: string;
    isLoading: boolean;
    darkMode: boolean;
    copiedId: string | null;
}