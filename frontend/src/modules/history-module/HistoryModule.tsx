import {
  Button,
  Callout,
  Card,
  DataList,
  Flex,
  Heading,
  ScrollArea,
  Text,
  Tooltip,
} from "@radix-ui/themes";
// import { useEffect } from "react";
import { valetudoApi } from "../../config/api/axios";
import { useMutation, useQuery } from "@tanstack/react-query";
import { DownloadIcon } from "@radix-ui/react-icons";
import { format } from "date-fns";
import { HelpComponent } from "@/components/HelpComponent";

export const HistoryModule = () => {
  const { mutate: downloadReport, isPending } = useMutation({
    mutationFn: async () => {
      const res = await valetudoApi.get("/doctor_report", {
        responseType: "blob",
        withCredentials: true,
      });

      const blob = new Blob([res.data]);
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "doctor_report.pdf";
      a.click();

      window.URL.revokeObjectURL(url);
    },
  });

  const { data: history = [] } = useQuery({
    queryKey: ["history_all"],
    queryFn: async () => {
      const res = await valetudoApi.get<
        Array<{
          timestamp: string;
          message: string;
          advice: string;
          bodyPart: string;
        }>
      >("/history_all");
      return res.data;
    },
  });

  console.log(history);

  return (
    <Flex direction="column" gap="2">
      <Tooltip content="Download report for doctor">
        <Button onClick={() => downloadReport()} loading={isPending}>
          Download report
          <DownloadIcon />
        </Button>
      </Tooltip>
      <ScrollArea style={{ maxHeight: "500px" }}>
        <Flex direction="column" gap="2">
          {history.length > 0 ? (
            history.map((history_item) => (
              <Card key={history_item.timestamp}>
                <Flex direction="column">
                  <Flex justify="between">
                    <Heading size="3" style={{ textTransform: "capitalize" }}>
                      {history_item.bodyPart}
                    </Heading>
                    <Text>{format(history_item.timestamp, "dd.MM.yyyy")}</Text>
                  </Flex>
                  <DataList.Root>
                    <DataList.Item>
                      <DataList.Label>Issue</DataList.Label>
                      <DataList.Value>{history_item.message}</DataList.Value>
                    </DataList.Item>
                  </DataList.Root>
                </Flex>
              </Card>
            ))
          ) : (
            <Callout.Root>
              <Callout.Text>
                No history records. Commicate with this AI assistant and records
                will appear
              </Callout.Text>
            </Callout.Root>
          )}
        </Flex>
      </ScrollArea>
      <HelpComponent content="History is the list of records of your deseases that you shared with us" />
    </Flex>
  );
};
