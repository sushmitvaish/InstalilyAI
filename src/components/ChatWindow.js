import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";

function ChatWindow() {
  const defaultMessage = [
    {
      role: "assistant",
      content:
        "Hi! I'm the **PartSelect Assistant**. I can help you with **refrigerator** and **dishwasher** parts.\n\n" +
        "I can help you:\n" +
        "- Find the right replacement part\n" +
        "- Check if a part fits your model\n" +
        "- Get installation instructions\n" +
        "- Troubleshoot common problems\n\n" +
        "What can I help you with today?",
      parts: [],
      suggested_queries: [
        "How can I install part PS11752778?",
        "My dishwasher is not draining",
        "Find parts for my Whirlpool refrigerator",
      ],
    },
  ];

  const [messages, setMessages] = useState(defaultMessage);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentPageUrl, setCurrentPageUrl] = useState(null);
  const [currentPageTitle, setCurrentPageTitle] = useState(null);
  const messagesEndRef = useRef(null);

  // Detect the currently open tab URL
  useEffect(() => {
    const chromeApi = window.chrome;

    const detectCurrentPage = async () => {
      try {
        if (chromeApi && chromeApi.tabs) {
          const [tab] = await chromeApi.tabs.query({
            active: true,
            currentWindow: true,
          });
          if (tab && tab.url && tab.url.includes("partselect.com")) {
            setCurrentPageUrl(tab.url);
            setCurrentPageTitle(tab.title || null);
          } else {
            setCurrentPageUrl(null);
            setCurrentPageTitle(null);
          }
        }
      } catch (e) {
        // Not running as extension or no permission — ignore
      }
    };

    detectCurrentPage();

    // Listen for tab changes
    if (chromeApi && chromeApi.tabs && chromeApi.tabs.onActivated) {
      const listener = () => detectCurrentPage();
      chromeApi.tabs.onActivated.addListener(listener);
      chromeApi.tabs.onUpdated.addListener(listener);
      return () => {
        chromeApi.tabs.onActivated.removeListener(listener);
        chromeApi.tabs.onUpdated.removeListener(listener);
      };
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const getConversationHistory = () => {
    return messages
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }));
  };

  const handleSend = async (text) => {
    const query = typeof text === "string" ? text : input;
    if (query.trim() === "" || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setInput("");
    setIsLoading(true);

    try {
      const history = getConversationHistory();
      const response = await getAIMessage(query, history, currentPageUrl);
      setMessages((prev) => [...prev, response]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong. Please try again.",
          parts: [],
          suggested_queries: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedClick = (query) => {
    handleSend(query);
  };

  return (
    <div className="messages-container">
      {messages.map((message, index) => (
        <div key={index} className={`${message.role}-message-container`}>
          {message.content && (
            <div className={`message ${message.role}-message`}>
              <div
                dangerouslySetInnerHTML={{
                  __html: marked(message.content).replace(/<p>|<\/p>/g, ""),
                }}
              ></div>
            </div>
          )}

          {/* Rich Part Cards */}
          {message.parts && message.parts.length > 0 && (
            <div className="part-cards-container">
              {message.parts.map((part, i) => (
                <a
                  key={i}
                  href={
                    part.part_url ||
                    `https://www.partselect.com/PS${part.ps_number}.htm`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="part-card"
                >
                  {part.image_url && (
                    <img
                      src={part.image_url}
                      alt={part.name}
                      className="part-card-image"
                    />
                  )}
                  <div className="part-card-info">
                    <div className="part-card-name">{part.name}</div>
                    <div className="part-card-ps">
                      PartSelect #{part.ps_number}
                    </div>
                    {part.oem_part_number && (
                      <div className="part-card-oem">
                        OEM: {part.oem_part_number}
                      </div>
                    )}
                    {part.price && (
                      <div className="part-card-price">{part.price}</div>
                    )}
                  </div>
                  <div className="part-card-arrow">&#8250;</div>
                </a>
              ))}
            </div>
          )}

          {/* Suggested Query Buttons - only on last assistant message */}
          {message.role === "assistant" &&
            message.suggested_queries &&
            message.suggested_queries.length > 0 &&
            index === messages.length - 1 && (
              <div className="suggested-queries">
                {message.suggested_queries.map((query, i) => (
                  <button
                    key={i}
                    className="suggested-btn"
                    onClick={() => handleSuggestedClick(query)}
                    disabled={isLoading}
                  >
                    {query}
                  </button>
                ))}
              </div>
            )}
        </div>
      ))}

      {/* Typing Indicator */}
      {isLoading && (
        <div className="assistant-message-container">
          <div className="message assistant-message typing-indicator">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />

      {/* Page context banner */}
      {currentPageUrl && (
        <div className="page-context-banner">
          <span className="page-context-icon">&#128279;</span>
          <span className="page-context-text">
            {currentPageTitle
              ? currentPageTitle.replace(/ – PartSelect\.com$/, "")
              : "Viewing a PartSelect page"}
          </span>
        </div>
      )}

      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about refrigerator or dishwasher parts..."
          disabled={isLoading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend(input);
            }
          }}
        />
        <button
          className="send-button"
          onClick={() => handleSend(input)}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;
