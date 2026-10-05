"use client";

import React, { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, X, Send, Mic, MicOff } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  role: string;
  avatar: string;
  isActive?: boolean;
}

interface Message {
  id: string;
  agentId: string;
  agentName: string;
  text: string;
  timestamp: Date;
  isMuted?: boolean;
}

const agents: Agent[] = [
  {
    id: "1",
    name: "MEDI Assistant",
    role: "Patient Intake",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=MEDI",
    isActive: true,
  },
  {
    id: "2",
    name: "Clinical Analyzer",
    role: "Symptom Analysis",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Clinical",
  },
  {
    id: "3",
    name: "Diagnosis Engine",
    role: "Medical Insights",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Diagnosis",
  },
  {
    id: "4",
    name: "Emergency Triage",
    role: "Urgent Assessment",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Emergency",
  },
  {
    id: "5",
    name: "Patient Memory",
    role: "Record Keeper",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Memory",
  },
  {
    id: "6",
    name: "Voice Assistant",
    role: "Real-time Voice",
    avatar: "https://api.dicebear.com/7.x/avataaars/svg?seed=Voice",
    isActive: true,
  },
];

const COLLAPSED_WIDTH = 280;
const EXPANDED_WIDTH = 420;
const EXPANDED_HEIGHT = 480;
const AVATAR_SIZE_COLLAPSED = 40;
const AVATAR_SIZE_EXPANDED = 52;

function SpeakingIndicator({ show }: { show: boolean }) {
  return (
    <div
      className={cn(
        "absolute -top-1 -right-1 bg-background rounded-full p-1.5 shadow-md",
        "transition-all duration-500 ease-out",
        show ? "opacity-100 scale-100" : "opacity-0 scale-0"
      )}
    >
      <div className="flex items-center justify-center gap-[2px]">
        <span className="w-[3px] h-[6px] bg-green-500 rounded-full animate-pulse" />
        <span
          className="w-[3px] h-[6px] bg-green-500 rounded-full animate-pulse"
          style={{ animationDelay: "0.1s" }}
        />
        <span
          className="w-[3px] h-[6px] bg-green-500 rounded-full animate-pulse"
          style={{ animationDelay: "0.2s" }}
        />
      </div>
    </div>
  );
}

function AudioWaveIcon({ isExpanded }: { isExpanded: boolean }) {
  return (
    <div
      className={cn(
        "absolute w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center",
        "transition-all duration-500 ease-out",
        isExpanded ? "opacity-0 scale-75" : "opacity-100 scale-100"
      )}
      style={{
        left: 12,
        top: "50%",
        transform: `translateY(-50%) ${isExpanded ? "scale(0.75)" : "scale(1)"}`,
      }}
    >
      <div className="flex items-center justify-center gap-[2px]">
        <span className="w-[3px] h-[6px] bg-white rounded-full animate-pulse" />
        <span
          className="w-[3px] h-[6px] bg-white rounded-full animate-pulse"
          style={{ animationDelay: "0.1s" }}
        />
        <span
          className="w-[3px] h-[6px] bg-white rounded-full animate-pulse"
          style={{ animationDelay: "0.2s" }}
        />
      </div>
    </div>
  );
}

function getAvatarPosition(index: number, isExpanded: boolean) {
  if (!isExpanded) {
    const startX = 60;
    return {
      x: startX + index * (AVATAR_SIZE_COLLAPSED + -8),
      y: 10,
      size: AVATAR_SIZE_COLLAPSED,
      opacity: index < 4 ? 1 : 0,
      scale: 1,
    };
  } else {
    const gridStartX = 28;
    const gridStartY = 80;
    const colWidth = 90;
    const rowHeight = 105;

    const col = index % 3;
    const row = Math.floor(index / 3);

    return {
      x: gridStartX + col * colWidth,
      y: gridStartY + row * rowHeight,
      size: AVATAR_SIZE_EXPANDED,
      opacity: 1,
      scale: 1,
    };
  }
}

export function MediAgentChat() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isMuted, setIsMuted] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isExpanded) {
      // Connect to WebSocket
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

      ws.onopen = () => {
        console.log("WebSocket connected");
        ws.send(
          JSON.stringify({
            type: "get_state",
          })
        );
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "transcript") {
          const newMessage: Message = {
            id: Math.random().toString(),
            agentId: data.role === "assistant" ? "1" : "user",
            agentName: data.role === "assistant" ? "MEDI Assistant" : "You",
            text: data.text,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, newMessage]);
        } else if (data.type === "patient_update") {
          console.log("Patient state updated:", data.data);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      wsRef.current = ws;

      return () => {
        ws.close();
      };
    }
  }, [isExpanded]);

  const sendMessage = () => {
    if (!inputValue.trim() || !wsRef.current) return;

    const userMessage: Message = {
      id: Math.random().toString(),
      agentId: "user",
      agentName: "You",
      text: inputValue,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);

    // Send to WebSocket
    wsRef.current.send(
      JSON.stringify({
        type: "transcript",
        role: "user",
        text: inputValue,
      })
    );

    setInputValue("");
  };

  const toggleRecording = () => {
    setIsRecording(!isRecording);
    if (!isRecording) {
      // Start recording
      if (wsRef.current) {
        wsRef.current.send(
          JSON.stringify({
            type: "start",
          })
        );
      }
    } else {
      // Stop recording
      if (wsRef.current) {
        wsRef.current.send(
          JSON.stringify({
            type: "stop",
          })
        );
      }
    }
  };

  return (
    <>
      <style jsx global>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>

      <div
        onClick={() => !isExpanded && setIsExpanded(true)}
        className={cn(
          "relative bg-slate-900 shadow-2xl border border-slate-700 overflow-hidden",
          "transition-all duration-500 ease-out",
          !isExpanded && "cursor-pointer hover:shadow-2xl hover:border-blue-500"
        )}
        style={{
          width: isExpanded ? EXPANDED_WIDTH : COLLAPSED_WIDTH,
          height: isExpanded ? EXPANDED_HEIGHT : 60,
          borderRadius: isExpanded ? 20 : 999,
        }}
      >
        {/* Audio Wave Icon */}
        <AudioWaveIcon isExpanded={isExpanded} />

        {/* +2 Counter (collapsed only) */}
        <div
          className={cn(
            "absolute flex items-center gap-0.5 text-slate-400",
            "transition-all duration-500 ease-out",
            isExpanded ? "opacity-0 pointer-events-none" : "opacity-100"
          )}
          style={{
            right: 16,
            top: "50%",
            transform: "translateY(-50%)",
          }}
        >
          <span className="text-sm font-medium">+2</span>
          <ChevronDown className="w-4 h-4" />
        </div>

        {/* Header (expanded only) */}
        <div
          className={cn(
            "absolute inset-x-0 top-0 flex items-center justify-between px-4 pt-3 pb-2 border-b border-slate-700",
            "transition-all duration-500 ease-out",
            isExpanded ? "opacity-100" : "opacity-0 pointer-events-none"
          )}
          style={{
            transitionDelay: isExpanded ? "100ms" : "0ms",
          }}
        >
          <div className="w-8" />
          <h2 className="text-sm font-semibold text-slate-100">MEDI AI Agents</h2>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(false);
            }}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-700 transition-colors"
          >
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Agents Grid */}
        <div
          className={cn(
            "absolute transition-all duration-500 ease-out",
            isExpanded ? "opacity-100" : "opacity-0"
          )}
          style={{
            top: 55,
            left: 0,
            right: 0,
            height: "120px",
            transitionDelay: isExpanded ? "150ms" : "0ms",
          }}
        >
          {agents.map((agent, index) => {
            const pos = getAvatarPosition(index, true);
            const delay = index * 30;

            return (
              <div
                key={agent.id}
                className="absolute transition-all duration-500 ease-out flex flex-col items-center"
                style={{
                  left: pos.x,
                  top: pos.y,
                  width: pos.size,
                  opacity: pos.opacity,
                  transitionDelay: `${delay}ms`,
                }}
              >
                <div className="relative">
                  <div
                    className="rounded-full overflow-hidden ring-2 ring-slate-600 shadow-lg transition-all duration-300 hover:ring-blue-500"
                    style={{
                      width: pos.size,
                      height: pos.size,
                    }}
                  >
                    <img
                      src={agent.avatar}
                      alt={agent.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <SpeakingIndicator show={agent.isActive ?? false} />
                </div>
                <span className="text-xs font-medium text-slate-300 mt-2 whitespace-nowrap">
                  {agent.name.split(" ")[0]}
                </span>
              </div>
            );
          })}
        </div>

        {/* Messages Area */}
        <div
          className={cn(
            "absolute overflow-y-auto bg-gradient-to-b from-slate-800 to-slate-900",
            "transition-all duration-500 ease-out",
            isExpanded ? "opacity-100" : "opacity-0 pointer-events-none"
          )}
          style={{
            top: 185,
            left: 0,
            right: 0,
            height: `${EXPANDED_HEIGHT - 260}px`,
            transitionDelay: isExpanded ? "200ms" : "0ms",
          }}
        >
          <div className="p-3 space-y-3 flex flex-col">
            {messages.length === 0 ? (
              <div className="text-center text-slate-500 text-sm py-4">
                Start a conversation with MEDI...
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={message.id}
                  className="animate-in fade-in-50 duration-300"
                  style={{
                    animation: `fadeIn 0.3s ease-out ${index * 50}ms`,
                    animationFillMode: "both",
                  }}
                >
                  <div
                    className={cn(
                      "text-xs font-semibold mb-1",
                      message.agentId === "user"
                        ? "text-blue-400"
                        : "text-emerald-400"
                    )}
                  >
                    {message.agentName}
                  </div>
                  <div
                    className={cn(
                      "text-xs leading-relaxed p-2 rounded-lg",
                      message.agentId === "user"
                        ? "bg-blue-600/20 text-slate-200"
                        : "bg-emerald-600/20 text-slate-200"
                    )}
                  >
                    {message.text}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div
          className={cn(
            "absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-900 to-slate-800 p-3 border-t border-slate-700",
            "transition-all duration-500 ease-out",
            isExpanded ? "opacity-100" : "opacity-0 pointer-events-none"
          )}
          style={{
            height: "75px",
            transitionDelay: isExpanded ? "250ms" : "0ms",
          }}
        >
          <div className="flex gap-2 mb-2">
            <button
              onClick={toggleRecording}
              className={cn(
                "flex-1 py-2 rounded-lg font-medium text-sm transition-all duration-200",
                isRecording
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              )}
            >
              {isRecording ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                  Recording...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Mic className="w-4 h-4" />
                  Voice
                </span>
              )}
            </button>
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="px-3 py-2 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600 transition-all duration-200"
            >
              {isMuted ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && sendMessage()}
              placeholder="Type message..."
              className="flex-1 px-3 py-2 rounded-lg bg-slate-700 text-slate-100 placeholder-slate-500 text-sm border border-slate-600 focus:border-blue-500 outline-none transition-colors"
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim()}
              className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
