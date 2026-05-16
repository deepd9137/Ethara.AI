import { z } from "zod";

// Read-only dashboard — no form schemas needed.
// Zod shapes kept for potential future filtering controls.

export const taskStatusSchema = z.enum(["todo", "in_progress", "in_review", "done"]);
export const taskPrioritySchema = z.enum(["low", "medium", "high", "critical"]);
