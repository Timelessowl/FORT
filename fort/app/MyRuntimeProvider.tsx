"use client";
 
import type { ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
} from "@assistant-ui/react";
 
const MyModelAdapter: ChatModelAdapter = {
  async run({ messages, abortSignal }) {
    const response = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
      signal: abortSignal,
    });

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No response body");

    const decoder = new TextDecoder();
    let content = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunks = decoder.decode(value).split('\n');
      for (const chunk of chunks) {
        if (!chunk.trim()) continue;
        try {
          const data = JSON.parse(chunk);
          if (data.content) {  // Handle content chunks
            content += data.content;
          }
        } catch (e) {
          console.error("Failed to parse chunk:", chunk);
        }
      }
    }

    return {
      content: [{ type: "text", text: content }],
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
