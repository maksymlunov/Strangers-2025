import { Flex, Select } from "@radix-ui/themes";
import type { FC } from "react";

type HumanBodyProps = {
  selectedBodyPart: string | null;
  onChange: (value: string) => void;
};

export const HumanBody: FC<HumanBodyProps> = ({
  selectedBodyPart,
  onChange,
}) => {
  return (
    <Flex justify="center" align="center" width="100%" height="100%">
      <Select.Root
        value={selectedBodyPart ?? ""}
        onValueChange={(value) => onChange(value)}
      >
        <Select.Trigger placeholder="Body part" />
        <Select.Content>
          <Select.Item value="head">Head</Select.Item>
          <Select.Item value="leg">Leg</Select.Item>
        </Select.Content>
      </Select.Root>
    </Flex>
  );
};
