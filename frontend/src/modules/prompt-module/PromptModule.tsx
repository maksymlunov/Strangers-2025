import {
  Flex,
  Container,
  Callout,
  Text,
  ScrollArea,
  Card,
} from "@radix-ui/themes";
import { InfoCircledIcon } from "@radix-ui/react-icons";
import { useState } from "react";
import { HumanScene } from "./HumanBody";
import { PromptInput } from "./PromptInput";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { valetudoApi } from "@/config/api/axios";

export type Message = {
  role: "assistant" | "user";
  message: string;
  timestamp: string | Date;
  bodyPart: string;
};

export const PromptModule = () => {
  const [bodyPart, setBodyPart] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const [messages, setMessages] = useState<Array<Message>>([]);

  const { mutateAsync, isPending } = useMutation({
    mutationFn: async (values: { message: string }) => {
      const res = await valetudoApi.post<{
        messages: Array<Message>;
      }>("/chat", {
        messages: [
          ...messages,
          {
            message: values.message,
            timestamp: new Date().toISOString(),
            role: "user",
            bodyPart,
          },
        ],
      });
      return res.data.messages;
    },
    mutationKey: ["chat"],
    onSuccess: (data) => {
      setMessages(data);
      queryClient.invalidateQueries({ queryKey: ["history_all"] });
    },
  });

  return (
    <Flex direction="column" flexGrow="1" overflow="hidden" position="relative">
      <HumanScene
        isDisabled={isPending}
        selectedBodyPart={bodyPart}
        handleSelectBodyPart={setBodyPart}
      />
      <Container size="3" mb="9" flexShrink="0">
        {bodyPart ? (
          <PromptInput
            mutate={mutateAsync}
            isLoading={isPending}
            bodyPart={bodyPart}
          />
        ) : (
          <Callout.Root size="3">
            <Callout.Icon>
              <InfoCircledIcon height="24px" width="24px" />
            </Callout.Icon>
            <Callout.Text weight="medium">
              You need to select body part that you are worried about.
            </Callout.Text>
          </Callout.Root>
        )}
      </Container>
      {bodyPart && (
        <Flex
          direction="column"
          align="center"
          style={{
            position: "absolute",
            top: "40px",
            left: "50%",
            transform: "translateX(-50%)",
            opacity: "70%",
          }}
        >
          <Text size="1">Selected</Text>
          <Text size="3" weight="medium">
            {bodyPart}
          </Text>
        </Flex>
      )}
      {messages.length > 0 ? (
        <ScrollArea style={{ position: "absolute", height: "80%" }} my="4">
          <Container size="4">
            <Flex direction="column" gap="2">
              {messages.map((message) => (
                <Flex
                  justify={message.role === "user" ? "end" : "start"}
                  key={message.timestamp.toString()}
                >
                  <Card style={{ maxWidth: "600px" }}>
                    <Text>{message.message}</Text>
                  </Card>
                </Flex>
              ))}
            </Flex>
          </Container>
        </ScrollArea>
      ) : null}
    </Flex>
  );
};
