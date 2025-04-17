"use client";

import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";

const MyModelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    let token: string | undefined;

    //#FIXME
    token = localStorage.getItem('token')
    if (!token) {
      throw new Error("Token is required for the Mermaid endpoint.");
    }

    const lastMessage = messages[messages.length - 1];
    const userText = lastMessage.content?.[0]?.text || "";
    if (!userText) {
      throw new Error("User message text is missing.");
    }

    let apiEndpoint: string;
    const type = localStorage.getItem('type') || "";
    const agentId =  Number(localStorage.getItem('agentId') ?? 0) + 1;

    if (type === 'mermaid') {
      apiEndpoint = '/api/v1/mermaid';
    } else if (agentId) {
      apiEndpoint = `/api/v1/chat/${agentId}`;
    } else {
      throw new Error("Neither agentId nor mermaid type specified in localStorage");
    }

    const requestBody = { token, text: userText };

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://192.168.1.111:8000";

    const response = await fetch(`${backendUrl}${apiEndpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
      signal: abortSignal,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Unknown error occurred");
    }
    if (type === 'mermaid') {
      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);
      return {
        content: [{ type: "image", src: imageUrl }],
        token,
      };
    } else {
      const data = await response.json();
      return {
        content: [{ type: "text", text: data.text }],
        token,
      };
    }
  },
};

export function MyRuntimeProvider({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const runtime = useLocalRuntime(MyModelAdapter);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}

