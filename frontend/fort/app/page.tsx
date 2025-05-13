"use client";

import { useState } from "react";
import { Thread } from "@/components/assistant-ui/thread";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
//import { useLocalRuntime } from "@assistant-ui/react";
import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { ThreadList } from "@/components/assistant-ui/thread-list";
import { StageList } from "@/components/assistant-ui/stage-list";

import { MyRuntimeProvider} from "@/app/MyRuntimeProvider";

export default function Home() {
  const [stageIndex, setStageIndex] = useState(0);
  //const runtime = useChatRuntime({ api: "/api/dummy" });
    //const runtime = useLocalRuntime({ adapter: MyModelAdapter});

  return (
    <MyRuntimeProvider>
      <main 
      className="
        h-dvh grid gap-x-2 px-4 py-4
        grid-cols-1
        md:grid-cols-[minmax(max-content,18rem)_1fr]
        2xl:grid-cols-[minmax(max-content,22rem)_1fr]
      ">
        {/* <ThreadList />*/}
        <StageList 
          stageIndex={stageIndex}
          onChangeStage={(newStage) => setStageIndex(newStage)}
        />
        <Thread stageIndex={stageIndex}/>
      </main>
    </MyRuntimeProvider>
  );
}

