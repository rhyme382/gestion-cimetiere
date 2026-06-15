import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from "@/lib/utils";
export function Separator({ className, orientation = "horizontal", ...props }) {
    return (_jsx("div", { role: "separator", className: cn("shrink-0 bg-border", orientation === "horizontal" ? "h-[1px] w-full" : "h-full w-[1px]", className), ...props }));
}
