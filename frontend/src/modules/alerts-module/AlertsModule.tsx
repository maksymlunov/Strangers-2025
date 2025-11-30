import { Card, Flex, Skeleton, Text } from "@radix-ui/themes";
import { useQuery } from "@tanstack/react-query";
import { valetudoApi } from "../../config/api/axios";
import { ExclamationTriangleIcon } from "@radix-ui/react-icons";

export const AlertsModule = () => {
  const { data = [] } = useQuery({
    queryKey: ["analize"],
    queryFn: async () => {
      const res = await valetudoApi.get<
        Array<{ risk: number; disease: string }>
      >("/analize");
      return res.data;
    },
  });

  return (
    <Flex direction="column" gap="2">
      {data.length > 0 ? (
        data.map((alert_item) => (
          <Card key={alert_item.disease}>
            <Flex gap="1" align="center">
              <Text
                weight="medium"
                style={{
                  textTransform: "capitalize",
                  flexGrow: 1,
                  whiteSpace: "normal",
                  overflowWrap: "anywhere",
                }}
              >
                {alert_item.disease}
              </Text>
              <ExclamationTriangleIcon
                style={{
                  flexShrink: 0,
                  width: "20px",
                  height: "20px",
                  color:
                    alert_item.risk >= 6
                      ? "var(--red-9)"
                      : alert_item.risk > 3
                      ? "var(--yellow-10)"
                      : undefined,
                }}
              />
            </Flex>
          </Card>
        ))
      ) : (
        <>
          <Skeleton>
            <Card>
              <Flex gap="1" align="center">
                <Text>Loading</Text>
              </Flex>
            </Card>
          </Skeleton>
          <Skeleton>
            <Card>
              <Flex gap="1" align="center">
                <Text>Loading</Text>
              </Flex>
            </Card>
          </Skeleton>
        </>
      )}
    </Flex>
  );
};
