import { Box, Card, Flex, Heading, Tabs } from "@radix-ui/themes";
import { Outlet } from "react-router-dom";
import { HistoryModule } from "../../modules/history-module/HistoryModule";
import { DevicesModule } from "../../modules/devices-module/DevicesModule";
import { AlertsModule } from "../../modules/alerts-module/AlertsModule";

const NAVIGATE_ITEMS = [
  { label: "Alerts", path: "alerts", content: <AlertsModule /> },
  { label: "History", path: "history", content: <HistoryModule /> },
  { label: "Devices", path: "devices", content: <DevicesModule /> },
];

export const RootLayout = () => {
  return (
    <Flex
      height="100dvh"
      direction="column"
      p="2"
      gap="2"
      minHeight="0px"
      overflow="hidden"
    >
      <Flex align="center" justify="between" minHeight="0px">
        <Heading>Valetudo</Heading>
      </Flex>
      <Flex width="100%" height="100%" gap="4">
        <Outlet />
        <Card>
          <Tabs.Root
            style={{
              width: "25vw",
              height: "100%",
            }}
            defaultValue={NAVIGATE_ITEMS[0].path}
          >
            <Tabs.List
              style={{ width: "100%", display: "flex", minHeight: "0px" }}
              size="2"
            >
              {NAVIGATE_ITEMS.map((item) => (
                <Tabs.Trigger
                  style={{ flex: 1 }}
                  key={item.path}
                  value={item.path}
                >
                  {item.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>
            <Box mt='2'>
              {NAVIGATE_ITEMS.map((item) => (
                <Tabs.Content key={item.path} value={item.path}>
                  {item.content}
                </Tabs.Content>
              ))}
            </Box>
          </Tabs.Root>
        </Card>
      </Flex>
    </Flex>
  );
};
