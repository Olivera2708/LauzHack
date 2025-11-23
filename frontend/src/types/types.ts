// types.ts
export interface Message {
    id: string;
    content: string;
    role: 'user' | 'assistant';
    timestamp: Date;
    image: string | undefined;
    local_url: string | undefined;
}
