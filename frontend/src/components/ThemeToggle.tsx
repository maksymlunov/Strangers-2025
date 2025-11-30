import { useTheme } from "next-themes";
import { SunIcon, MoonIcon } from "@radix-ui/react-icons";
import { IconButton, Tooltip } from "@radix-ui/themes";

export const ThemeToggle = () => {
  const { resolvedTheme, setTheme } = useTheme();

  const isDark = resolvedTheme === "dark";

  return (
    <Tooltip content="Toggle theme">
      <IconButton
        radius="full"
        size="2"
        variant="surface"
        onClick={() => setTheme(isDark ? "light" : "dark")}
      >
        {isDark ? (
          <SunIcon width={18} height={18} />
        ) : (
          <MoonIcon width={18} height={18} />
        )}
      </IconButton>
    </Tooltip>
  );
};
