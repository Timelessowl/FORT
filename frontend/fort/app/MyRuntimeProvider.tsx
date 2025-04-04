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

    #FIXME
    token = "ce7cbfe4-a388-4fa2-bc53-ba0acce26742"
    if (!token) {
      throw new Error("Token is required for the Mermaid endpoint.");
    }

    const lastMessage = messages[messages.length - 1];
    const userText = lastMessage.content?.[0]?.text || "";
    if (!userText) {
      throw new Error("User message text is missing.");
    }

    const requestBody = { token, text: userText };

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://192.168.1.111:8000";

    const response = await fetch(`${backendUrl}/api/v1/mermaid`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
      signal: abortSignal,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Unknown error occurred");
    }
    const blob = await response.blob();
    const imageUrl = URL.createObjectURL(blob);
    return {
        content: [{ type: "image", src: imageUrl }],
        token,
    };
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

