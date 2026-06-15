import { jsx as _jsx } from "react/jsx-runtime";
import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";
const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors", {
    variants: {
        variant: {
            default: "border-transparent bg-primary text-primary-foreground",
            secondary: "border-transparent bg-secondary text-secondary-foreground",
            outline: "text-foreground",
            success: "border-transparent bg-green-100 text-green-800",
            warning: "border-transparent bg-orange-100 text-orange-800",
            danger: "border-transparent bg-red-100 text-red-800",
            info: "border-transparent bg-blue-100 text-blue-800",
            purple: "border-transparent bg-purple-100 text-purple-800",
            muted: "border-transparent bg-gray-100 text-gray-700",
        },
    },
    defaultVariants: { variant: "default" },
});
export function Badge({ className, variant, ...props }) {
    return _jsx("div", { className: cn(badgeVariants({ variant }), className), ...props });
}
