import { Flex, Container, Callout } from "@radix-ui/themes";
import { InfoCircledIcon } from "@radix-ui/react-icons";
import { useState } from "react";
import { HumanBody } from "./HumanBody";
import { PromptInput } from "./PromptInput";

export const PromptModule = () => {
  const [bodyPart, setBodyPart] = useState<string | null>(null);

  return (
    <Flex direction="column" flexGrow='1'>
      <HumanBody selectedBodyPart={bodyPart} onChange={(v) => setBodyPart(v)} />
      <Container size="3" mb="9">
        {bodyPart ? (
          <PromptInput bodyPart={bodyPart} />
        ) : (
          <Callout.Root size="3" color="gray">
            <Callout.Icon>
              <InfoCircledIcon />
            </Callout.Icon>
            <Callout.Text>
              You need to select body part that you are worried about.
            </Callout.Text>
          </Callout.Root>
        )}
      </Container>
    </Flex>
  );
};
