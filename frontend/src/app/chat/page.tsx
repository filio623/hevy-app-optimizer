'use client';

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // Add a useEffect to log when the component mounts
  useEffect(() => {
    console.log('Chat component mounted');
  }, []);

  // useEffect for auto-scrolling
  useEffect(() => {
    if (chatContainerRef.current) {
      // Scroll to the bottom smoothly
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages]); // Dependency array ensures this runs when messages change

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    console.log('Submitting message:', userMessage);
    setInput('');
    setIsLoading(true);

    try {
      // Add user message to chat
      setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

      // Use environment variable for backend URL
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'; // Fallback for safety
      console.log(`Sending request to API at: ${apiUrl}/api/chat/`);
      
      const response = await fetch(`${apiUrl}/api/chat/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      console.log('API response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API error response:', errorText);
        throw new Error(`Failed to get response: ${response.status} ${errorText}`);
      }

      const data = await response.json();
      console.log('API response data:', data);
      
      // Add assistant response to chat
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error) {
      console.error('Error in handleSubmit:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error. Please try again.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      {/* Chat messages */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {message.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none dark:prose-invert whitespace-pre-wrap">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  message.content
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-900 rounded-lg p-4">
                <span className="typing-animation">Thinking</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input form */}
      <div className="border-t p-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your workout program..."
            className="flex-1 p-4 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder-gray-400 text-black"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-4 bg-blue-500 text-white rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
} 