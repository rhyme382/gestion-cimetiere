import { jsx as _jsx } from "react/jsx-runtime";
import { cn } from "@/lib/utils";
import { forwardRef } from "react";
export const Input = forwardRef(({ className, type, ...props }, ref) => (_jsx("input", { type: type, ref: ref, className: cn("flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50", className), ...props })));
Input.displayName = "Input";
