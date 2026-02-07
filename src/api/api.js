const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export const getAIMessage = async (userQuery, conversationHistory = [], pageUrl = null) => {
  try {
    const body = {
      message: userQuery,
      conversation_history: conversationHistory,
    };
    if (pageUrl) {
      body.page_url = pageUrl;
    }

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return {
      role: "assistant",
      content: data.content,
      parts: data.parts || [],
      suggested_queries: data.suggested_queries || [],
    };
  } catch (error) {
    console.error("API call failed:", error);
    return {
      role: "assistant",
      content:
        "I'm sorry, I'm having trouble connecting right now. Please try again in a moment.",
      parts: [],
      suggested_queries: [
        "Help me find a refrigerator part",
        "My dishwasher needs repair",
      ],
    };
  }
};
