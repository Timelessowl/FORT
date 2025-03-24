// /api/chat/route.ts
import { jsonSchema, streamText } from "ai";
import { openai } from "@ai-sdk/openai"; // in production you might use this

export const maxDuration = 30;

export async function POST(req: Request) {
  // Parse the incoming request
  const { messages, system, tools } = await req.json();

  // For a custom local backend, we simulate a reply without consuming tokens.
  // Here we generate a placeholder answer.
  const lastUserMessage = messages[messages.length - 1];
  const dummyText = `Hello! You said: "${lastUserMessage.content}". This is a dummy response.`;
  const imageUrl = "https://via.placeholder.com/300.png?text=Placeholder+Image";
  // Using Markdown for the image so the frontend renders it.
  const dummyImageMarkdown = ` ![Placeholder Image](${imageUrl})`;

  // Build the streaming response as NDJSON.
  // Each line must be a complete JSON object followed by a newline.
  // The official docs require the chunk format to be like <type>:<JSON>, so we choose a type that is handled (for example, "data").
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      // First, send a metadata chunk. This helps the client correlate thread/message IDs.
      // (Dummy values are used here.)
      controller.enqueue(
        encoder.encode(JSON.stringify({ threadId: "local-thread", messageId: "local-msg" }) + "\n")
      );
      // Next, stream the assistant's text response.
      controller.enqueue(
        encoder.encode("data:" + JSON.stringify({ content: dummyText }) + "\n")
      );
      // Finally, stream the image markdown.
      controller.enqueue(
        encoder.encode("data:" + JSON.stringify({ content: dummyImageMarkdown }) + "\n")
      );
      controller.close();
    },
  });

  // Return the streaming response with the NDJSON content type.
  return new Response(stream, {
    headers: { "Content-Type": "application/x-ndjson" },
  });
}

