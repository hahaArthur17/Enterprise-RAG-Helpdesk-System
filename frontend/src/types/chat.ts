// Define the shape of a chat message
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}