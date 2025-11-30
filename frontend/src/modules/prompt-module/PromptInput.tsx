import { PaperPlaneIcon } from "@radix-ui/react-icons";
import { Flex, TextArea, Button } from "@radix-ui/themes";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { valetudoApi } from "../../config/api/axios";

type PromtFormValue = {
  message: string;
};

export const PromptInput = ({ bodyPart }: { bodyPart: string }) => {
  const queryClinet = useQueryClient();

  const { register, handleSubmit } = useForm<PromtFormValue>({});

  const { mutate, isPending } = useMutation({
    mutationFn: async (values: PromtFormValue & { bodyPart: string }) => {
      const res = await valetudoApi.post("/history", values);
      return res.data;
    },
    onSuccess: () => {
      queryClinet.invalidateQueries({ queryKey: ["history_all"] });
    },
  });

  const handleSendMessage = (values: PromtFormValue) => {
    mutate({ ...values, bodyPart });
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
          <Button color="cyan" type="submit" loading={isPending}>
            Send <PaperPlaneIcon />
          </Button>
        </Flex>
      </Flex>
    </form>
  );
};
