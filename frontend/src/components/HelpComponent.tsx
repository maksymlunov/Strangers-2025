import { InfoCircledIcon } from "@radix-ui/react-icons";
import { Flex, Tooltip, Text } from "@radix-ui/themes";
import type { FC } from "react";

type HelpComponentProps = {
  content: string;
};

export const HelpComponent: FC<HelpComponentProps> = ({ content }) => {
  return (
    <Flex justify="end">
      <Tooltip content={content}>
        <Flex gap="1" align="center">
          <Text>Help</Text>
          <InfoCircledIcon />
        </Flex>
      </Tooltip>
    </Flex>
  );
};
