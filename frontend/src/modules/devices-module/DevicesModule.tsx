import {
  Button,
  Card,
  RadioCards,
  Flex,
  ScrollArea,
  Text,
  DataList,
  Callout,
} from "@radix-ui/themes";
import { useQuery } from "@tanstack/react-query";
import { valetudoApi } from "../../config/api/axios";
import { PlusIcon } from "@radix-ui/react-icons";
import { useState } from "react";
import { format } from "date-fns";
import { startCase } from "lodash";

// this logic will be improved
const connectDevice = async () => {
  // @ts-expect-error extended types with bluetooth not specified
  const device = await navigator.bluetooth.requestDevice({
    filters: [{ services: ["heart_rate"] }],
  });
  console.log(device);
};

export const DevicesModule = () => {
  const [device, setDevice] = useState<string | null>(null);

  const { data: devices } = useQuery({
    queryKey: ["devices"],
    queryFn: async () => {
      const res = await valetudoApi.get<string[]>("/devices");
      return res.data;
    },
  });
  const { data: devicesData = [] } = useQuery({
    queryKey: ["devices-data"],
    queryFn: async () => {
      const res = await valetudoApi.get<
        {
          device: string;
          sessions: Array<Record<string, number> & { timestamp: string }>;
        }[]
      >("/devices_data");
      return res.data;
    },
  });

  const selectedDeviceSessions =
    devicesData.find((item) => item.device === device)?.sessions ?? [];

  return (
    <Flex direction="column" gap="2">
      <ScrollArea>
        <RadioCards.Root
          value={device}
          gap="2"
          onValueChange={(v) => setDevice(v)}
          style={{ maxHeight: "300px" }}
        >
          {devices?.map((device) => (
            <RadioCards.Item
              value={device}
              key={device}
              style={{ flexShrink: 0 }}
            >
              <Text size="2" weight="medium">
                {device}
              </Text>
            </RadioCards.Item>
          ))}
        </RadioCards.Root>
      </ScrollArea>
      {device && (
        <ScrollArea>
          <Flex maxHeight="400px" direction="column" gap="2" py="1">
            {selectedDeviceSessions?.length > 0 ? (
              selectedDeviceSessions?.map((session) => (
                <Card key={session.timestamp} style={{ flexShrink: 0 }}>
                  <DataList.Root>
                    {Object.keys(session)
                      .filter((key) => key !== "timestamp")
                      .map((key) => (
                        <DataList.Item key={key}>
                          <DataList.Label>{startCase(key)}</DataList.Label>
                          <DataList.Value>{session[key]}</DataList.Value>
                        </DataList.Item>
                      ))}
                    <DataList.Item>
                      <DataList.Label>Date</DataList.Label>
                      <DataList.Value>
                        {format(session.timestamp, "dd.MM.yyyy")}
                      </DataList.Value>
                    </DataList.Item>
                  </DataList.Root>
                </Card>
              ))
            ) : (
              <Callout.Root>
                <Callout.Text>No data from device</Callout.Text>
              </Callout.Root>
            )}
          </Flex>
        </ScrollArea>
      )}
      <Button onClick={connectDevice}>
        Connect device <PlusIcon />
      </Button>
    </Flex>
  );
};
