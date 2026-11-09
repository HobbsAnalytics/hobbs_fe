import React, { createContext, useContext } from 'react';
import { useChat } from '../../hooks/useChat';

// The chat session lives above the routes, so opening a drawing from a source chip and coming back keeps the
// conversation (and its conversation_id for follow-ups).
export type ChatSession = ReturnType<typeof useChat>;

export const ChatContext = createContext<ChatSession | null>(null);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const chat = useChat();
  return <ChatContext.Provider value={chat}>{children}</ChatContext.Provider>;
};

export function useChatSession(): ChatSession | null {
  return useContext(ChatContext);
}
