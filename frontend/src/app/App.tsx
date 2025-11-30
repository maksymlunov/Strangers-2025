import { useRoutes } from "react-router-dom";
import { RootLayout } from "./layouts/RootLayout";
import { PromptModule } from "@/modules/prompt-module/PromptModule";

export const App = () => {
  const routes = useRoutes([
    {
      element: <RootLayout />,
      children: [{ path: "/", element: <PromptModule /> }],
    },
  ]);

  return routes;
};
