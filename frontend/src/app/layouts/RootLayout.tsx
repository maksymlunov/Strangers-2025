import { Box, Card, Flex, Tabs, Tooltip } from "@radix-ui/themes";
import { Outlet } from "react-router-dom";
import { HistoryModule } from "../../modules/history-module/HistoryModule";
import { DevicesModule } from "../../modules/devices-module/DevicesModule";
import { AlertsModule } from "../../modules/alerts-module/AlertsModule";
import Logo from "../../../assets/logo.svg?react";
import {
  CountdownTimerIcon,
  ExclamationTriangleIcon,
  MobileIcon,
  QuestionMarkCircledIcon,
} from "@radix-ui/react-icons";

const NAVIGATE_ITEMS = [
  {
    label: "Alerts",
    icon: <ExclamationTriangleIcon />,
    path: "alerts",
    content: <AlertsModule />,
  },
  {
    label: "History",
    icon: <CountdownTimerIcon />,
    path: "history",
    content: <HistoryModule />,
  },
  {
    label: "Devices",
    icon: <MobileIcon />,
    path: "devices",
    content: <DevicesModule />,
  },
];

export const RootLayout = () => {
  return (
    <Flex height="100dvh" p="2" gap="2" minHeight="0px" overflow="hidden">
      <Flex flexGrow="1" direction="column">
        <Flex align="center" justify="between" minHeight="0px" flexShrink="0">
          <Logo />
          <Tooltip content="This application is AI Assistent that helps to monitor your health. It collects data from your smart devices, agregates it and uses for future risk and problem analysis">
            <QuestionMarkCircledIcon />
          </Tooltip>
        </Flex>
        <Outlet />
      </Flex>
      <Card>
        <Tabs.Root
          style={{
            width: "25vw",
            height: "100%",
            flexShrink: 0,
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
                <Flex align="center" gap="1">
                  {item.label} {item.icon}
                </Flex>
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          <Box mt="2">
            {NAVIGATE_ITEMS.map((item) => (
              <Tabs.Content key={item.path} value={item.path}>
                {item.content}
              </Tabs.Content>
            ))}
          </Box>
        </Tabs.Root>
      </Card>
    </Flex>
  );
};
