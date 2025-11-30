import { PaperPlaneIcon } from "@radix-ui/react-icons";
import { Flex, TextArea, Button } from "@radix-ui/themes";
import { useForm } from "react-hook-form";

type PromtFormValue = {
  message: string;
};

export const PromptInput = ({
  mutate,
  isLoading,
}: {
  bodyPart: string;
  isLoading: boolean;
  mutate: (values: PromtFormValue) => Promise<unknown>;
}) => {
  const { register, handleSubmit, reset } = useForm<PromtFormValue>({
    disabled: isLoading,
  });

  const handleSendMessage = async (values: PromtFormValue) => {
    await mutate({ ...values });
    reset();
  };

  return (
    <form onSubmit={handleSubmit(handleSendMessage)}>
      <Flex direction="column" gap="1">
        <TextArea
          {...register("message")}
          size="3"
          placeholder="Enter your problem. For example: it hurts..."
        />
        <Flex justify="end">
          <Button color="cyan" type="submit" loading={isLoading}>
            Send <PaperPlaneIcon />
          </Button>
        </Flex>
      </Flex>
    </form>
  );
};
