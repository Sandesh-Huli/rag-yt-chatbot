import { useState, useEffect, useRef } from 'react';
import { useContext } from 'react';
import { AppContext } from '../context/AppContext.jsx';
import { ChatContext } from '../context/ChatContext.jsx';

export default function Chat() {
    const { chatHistory } = useContext(ChatContext); // Assuming you store chat history in context
    const chatEndRef = useRef(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    if (!chatHistory || chatHistory.length === 0) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-500">
                <p>No messages yet. Start a conversation!</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-96 bg-gray-50 rounded-lg p-4 overflow-y-auto">
            <div className="flex-1 space-y-4">
                {chatHistory.map((message, index) => (
                    <div
                        key={index}
                        className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`
                                max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow
                                ${message.sender === 'user'
                                    ? 'bg-blue-600 text-white rounded-br-none'
                                    : 'bg-white text-gray-800 rounded-bl-none border'
                                }
                            `}
                        >
                            {/* Message sender label */}
                            <div className={`text-xs mb-1 ${message.sender === 'user' ? 'text-blue-100' : 'text-gray-500'}`}>
                                {message.sender === 'user' ? 'You' : 'AI Assistant'}
                            </div>
                            
                            {/* Message content */}
                            <div className="text-sm leading-relaxed">
                                {message.content}
                            </div>
                            
                            {/* Timestamp */}
                            <div className={`text-xs mt-1 ${message.sender === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                                {message.timestamp ? new Date(message.timestamp).toLocaleTimeString() : ''}
                            </div>
                        </div>
                    </div>
                ))}
                
                {/* Typing indicator (optional) */}
                {/* {isTyping && (
                    <div className="flex justify-start">
                        <div className="bg-white text-gray-800 px-4 py-2 rounded-lg border">
                            <div className="flex space-x-1">
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                            </div>
                        </div>
                    </div>
                )} */}
            </div>
            
            {/* Auto-scroll anchor */}
            <div ref={chatEndRef} />
        </div>
    );
}