import { PaperPlaneIcon } from "@radix-ui/react-icons";
import { Flex, TextArea, Button } from "@radix-ui/themes";
import { useRef, useState } from "react";
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
  const { register, handleSubmit, reset, setValue, watch } =
    useForm<PromtFormValue>({
      disabled: isLoading,
    });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any | null>(null);
  const [recording, setRecording] = useState(false);

  const recognizeVoice = () => {
    const SpeechRecognition =
      // @ts-expect-error need to expand types to include speech recognition
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Your browser does not support speech recognition");
      return;
    }

    if (!recording) {
      const recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;

      // eslint-disable-next-line
      recognition.onresult = (event: any) => {
        const text = event.results[0][0].transcript;
        console.log(text);
        // eslint-disable-next-line
        const current = watch("message") ?? "";
        setValue("message", current + (current ? " " : "") + text);
      };

      recognition.onend = () => {
        setRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
      setRecording(true);
    } else {
      recognitionRef.current?.stop();
      recognitionRef.current = null;
      setRecording(false);
    }
  };

  const handleSendMessage = async (values: PromtFormValue) => {
    await mutate(values);
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

        <Flex justify="end" gap="1">
          <Button
            type="button"
            onClick={recognizeVoice}
            color={recording ? "red" : "gray"}
          >
            {recording ? "Stop" : "Voice"}
          </Button>

          <Button color="cyan" type="submit" loading={isLoading}>
            Send <PaperPlaneIcon />
          </Button>
        </Flex>
      </Flex>
    </form>
  );
};
