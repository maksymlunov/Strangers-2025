import { useRoutes } from "react-router-dom";
import { RootLayout } from "./layouts/RootLayout";
import { HomePage } from "../pages/HomePage";

export const App = () => {
  const routes = useRoutes([
    {
      element: <RootLayout />,
      children: [
        { path: "/", element: <HomePage /> },
        { path: "/devices", element: "Devices" },
        { path: "/history", element: "History" },
        { path: "/alerts", element: "Alerts" },
      ],
    },
  ]);

  return routes;
};
