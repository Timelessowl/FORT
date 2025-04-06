import type { FC } from "react";
import { useState } from "react";
import {
  ThreadListItemPrimitive,
  ThreadListPrimitive,
} from "@assistant-ui/react";
import { Button } from "@/components/ui/button";

export const StageList: FC = () => {
  const stages = [
    { id: "stage-1", title: "Stage 1: Initiation" },
    { id: "stage-2", title: "Stage 2: Development" },
    { id: "stage-3", title: "Stage 3: Completion" },
  ];

  const [activeStage, setActiveStage] = useState(0);

  const handleNext = () => {
    if (activeStage < stages.length - 1) {
      setActiveStage((prev) => prev + 1);
    }
  };

  return (
    <ThreadListPrimitive.Root className="flex flex-col items-stretch gap-1.5">
      <StageNextButton
        activeStage={activeStage}
        totalStages={stages.length}
        onNext={handleNext}
      />
      <StageListItems stages={stages} activeStage={activeStage} />
    </ThreadListPrimitive.Root>
  );
};

interface StageListItemsProps {
  stages: { id: string; title: string }[];
  activeStage: number;
}

const StageListItems: FC<StageListItemsProps> = ({ stages, activeStage }) => {
  return (
    <>
      {stages.map((stage, index) => (
        <StageListItem
          key={stage.id}
          stageTitle={stage.title}
          threadId={stage.id}
          isActive={index === activeStage}
        />
      ))}
    </>
  );
};

interface StageListItemProps {
  stageTitle: string;
  threadId: string;
  isActive: boolean;
}

const StageListItem: FC<StageListItemProps> = ({
  stageTitle,
  threadId,
  isActive,
}) => {
  return (
    <ThreadListItemPrimitive.Root
      data-thread-id={threadId}
      className={`flex items-center gap-2 rounded-lg transition-all focus-visible:outline-none focus-visible:ring-2 ${
        isActive ? "bg-white" : "bg-gray-200"
      }`}
    >
      <ThreadListItemPrimitive.Trigger className="flex-grow px-3 py-2 text-start">
        <p
          className={`text-sm font-medium ${
            isActive ? "text-black" : "text-gray-500"
          }`}
        >
          {stageTitle}
        </p>
      </ThreadListItemPrimitive.Trigger>
    </ThreadListItemPrimitive.Root>
  );
};

interface StageNextButtonProps {
  activeStage: number;
  totalStages: number;
  onNext: () => void;
}

const StageNextButton: FC<StageNextButtonProps> = ({
  activeStage,
  totalStages,
  onNext,
}) => {
  return (
    <ThreadListPrimitive.New asChild>
      <Button
        onClick={onNext}
        disabled={activeStage >= totalStages - 1}
        className="data-[active]:bg-muted hover:bg-muted flex items-center justify-start gap-1 rounded-lg px-2.5 py-2 text-start"
        variant="ghost"
      >
        Next Stage
      </Button>
    </ThreadListPrimitive.New>
  );
};

