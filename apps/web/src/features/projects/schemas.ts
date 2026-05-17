import { z } from "zod";

export const createProjectSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(80),
  description: z.string().max(2000).optional().default(""),
});
export type CreateProjectFormData = z.infer<typeof createProjectSchema>;

export const updateProjectSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(80),
  description: z.string().max(2000).optional().default(""),
});
export type UpdateProjectFormData = z.infer<typeof updateProjectSchema>;

export const inviteMemberSchema = z.object({
  email: z.string().email("Enter a valid email"),
  role: z.enum(["admin", "member"]).default("member"),
});
export type InviteMemberFormData = z.infer<typeof inviteMemberSchema>;
