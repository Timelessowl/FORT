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

    token = localStorage.getItem('token')
    if (!token) {
      throw new Error("Token is required for the Mermaid endpoint.");
    }

    const lastMessage = messages.at(-1);
    const rawText = lastMessage?.content?.[0]?.text ?? "";
    if (!rawText) throw new Error("User message text is missing.");

    const texts = rawText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    let apiEndpoint: string;
    const type = localStorage.getItem('type') || "";
    const isMermaid = type === "mermaid";
    const agentId =  Number(localStorage.getItem('agentId') ?? 0) + 1;

    if (type === 'mermaid') {
      apiEndpoint = '/api/v1/mermaid';
    } else if (agentId) {
      apiEndpoint = `/api/v1/chat/${agentId}`;
    } else {
      throw new Error("Neither agentId nor mermaid type specified in localStorage");
    }

    // const requestBody = { token, text: userText };

  const requestBody = isMermaid
    ? { token, texts: rawText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean) }
    : { token, text: rawText };

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "";

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
    if (type === "mermaid") {
      const { images } = await response.json();
      const content = (images as string[]).map((b64) => ({
        type: "image" as const,
        src: `data:image/png;base64,${b64}`,
      }));
      return { content, token };
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

