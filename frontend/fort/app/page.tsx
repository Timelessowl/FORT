"use client";
import { Thread } from "@/components/assistant-ui/thread";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
//import { useLocalRuntime } from "@assistant-ui/react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { ThreadList } from "@/components/assistant-ui/thread-list";
import { StageList } from "@/components/assistant-ui/stage-list";

import { MyRuntimeProvider} from "@/app/MyRuntimeProvider";

export default function Home() {
  //const runtime = useChatRuntime({ api: "/api/dummy" });
    //const runtime = useLocalRuntime({ adapter: MyModelAdapter});

  return (
    <MyRuntimeProvider>
      <main className="h-dvh grid grid-cols-[200px_1fr] gap-x-2 px-4 py-4">
        {/* <ThreadList />*/}
        <StageList />
        <Thread />
      </main>
    </MyRuntimeProvider>
  );
}
