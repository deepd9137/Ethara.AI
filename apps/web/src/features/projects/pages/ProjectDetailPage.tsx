import { useState, useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Dialog,
  EmptyState,
  ErrorBoundary,
  Input,
  MemberListSkeleton,
  Select,
  Skeleton,
  TaskListSkeleton,
  Textarea,
} from "@/components/ui";
import { useAuthStore } from "@/store/auth";
import { useCreateShortcut } from "@/lib/hooks/useKeyboardShortcuts";
import { ALLOWED_TRANSITIONS, type TaskResponse, type TaskStatus } from "@/features/tasks/api";
import {
  useCreateTask,
  useDeleteTask,
  useTasks,
  useTransitionStatus,
  useUpdateTask,
} from "@/features/tasks/hooks";
import { createTaskSchema, type CreateTaskFormData } from "@/features/tasks/schemas";
import {
  useChangeMemberRole,
  useDeleteProject,
  useInviteMember,
  useMembers,
  useProject,
  useRemoveMember,
  useUpdateProject,
} from "../hooks";
import type { MemberResponse, ProjectRole } from "../api";
import {
  createProjectSchema,
  inviteMemberSchema,
  type CreateProjectFormData,
  type InviteMemberFormData,
} from "../schemas";

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_LABELS: Record<TaskStatus, string> = {
  todo: "To Do",
  in_progress: "In Progress",
  in_review: "In Review",
  done: "Done",
};

const STATUS_COLOURS: Record<TaskStatus, string> = {
  todo: "bg-surface border-border text-muted",
  in_progress: "bg-info/10 border-info/30 text-info",
  in_review: "bg-warning/10 border-warning/30 text-warning",
  done: "bg-success/10 border-success/30 text-success",
};

const PRIORITY_COLOURS: Record<string, string> = {
  critical: "text-danger",
  high: "text-orange-500",
  medium: "text-yellow-500",
  low: "text-muted",
};

function formatDate(dateStr: string | null) {
  if (!dateStr) return null;
  return new Date(dateStr + "T00:00:00").toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// ── Task dialogs ───────────────────────────────────────────────────────────────

function CreateTaskDialog({
  projectId,
  members,
  open,
  onOpenChange,
}: {
  projectId: string;
  members: MemberResponse[];
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const create = useCreateTask(projectId);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateTaskFormData>({ resolver: zodResolver(createTaskSchema) });

  async function onSubmit(data: CreateTaskFormData) {
    await create.mutateAsync({
      ...data,
      assignee_id: data.assignee_id || null,
      due_date: data.due_date || null,
    });
    reset();
    onOpenChange(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
      title="New task"
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="Title"
          placeholder="e.g. Design homepage mockup"
          error={errors.title?.message}
          {...register("title")}
        />
        <Textarea
          label="Description"
          placeholder="Optional details…"
          {...register("description")}
        />
        <div className="grid grid-cols-2 gap-3">
          <Select label="Priority" {...register("priority")}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </Select>
          <Select label="Assignee" {...register("assignee_id")}>
            <option value="">Unassigned</option>
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.user.name}
              </option>
            ))}
          </Select>
        </div>
        <Input label="Due date" type="date" {...register("due_date")} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={create.isPending}>
            Create
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function EditTaskDialog({
  projectId,
  task,
  members,
  open,
  onOpenChange,
}: {
  projectId: string;
  task: TaskResponse;
  members: MemberResponse[];
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const update = useUpdateTask(projectId);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CreateTaskFormData>({
    resolver: zodResolver(createTaskSchema),
    defaultValues: {
      title: task.title,
      description: task.description,
      priority: task.priority,
      assignee_id: task.assignee_id ?? undefined,
      due_date: task.due_date ?? undefined,
    },
  });

  async function onSubmit(data: CreateTaskFormData) {
    await update.mutateAsync({
      taskId: task.id,
      payload: { ...data, assignee_id: data.assignee_id || null, due_date: data.due_date || null },
      updatedAt: task.updated_at,
    });
    onOpenChange(false);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Edit task">
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input label="Title" error={errors.title?.message} {...register("title")} />
        <Textarea label="Description" {...register("description")} />
        <div className="grid grid-cols-2 gap-3">
          <Select label="Priority" {...register("priority")}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </Select>
          <Select label="Assignee" {...register("assignee_id")}>
            <option value="">Unassigned</option>
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.user.name}
              </option>
            ))}
          </Select>
        </div>
        <Input label="Due date" type="date" {...register("due_date")} />
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={update.isPending}>
            Save
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

// ── Task row ──────────────────────────────────────────────────────────────────

function TaskRow({
  task,
  projectId,
  members,
  currentUserId,
  isAdmin,
}: {
  task: TaskResponse;
  projectId: string;
  members: MemberResponse[];
  currentUserId: string;
  isAdmin: boolean;
}) {
  const [editOpen, setEditOpen] = useState(false);
  const deleteTask = useDeleteTask(projectId);
  const transition = useTransitionStatus(projectId);
  const assigneeName = members.find((m) => m.user_id === task.assignee_id)?.user.name;
  const canEdit =
    isAdmin || task.creator_id === currentUserId || task.assignee_id === currentUserId;
  const nextStatuses = ALLOWED_TRANSITIONS[task.status];

  return (
    <>
      {/* Desktop row */}
      <div className="border-border hidden items-center gap-3 border-b py-3 last:border-0 sm:flex">
        <div className="min-w-0 flex-1">
          <p className="text-body truncate text-sm font-medium">{task.title}</p>
          <p className={`text-xs font-medium ${PRIORITY_COLOURS[task.priority]}`}>
            {task.priority}
            {assigneeName && <span className="text-muted font-normal"> · {assigneeName}</span>}
            {task.due_date && (
              <span className="text-muted font-normal"> · {formatDate(task.due_date)}</span>
            )}
          </p>
        </div>
        <select
          value={task.status}
          onChange={(e) =>
            transition.mutate({
              taskId: task.id,
              status: e.target.value as TaskStatus,
              updatedAt: task.updated_at,
            })
          }
          className={`cursor-pointer rounded-full border px-2.5 py-0.5 text-xs font-medium outline-none ${STATUS_COLOURS[task.status]}`}
          aria-label={`Task status: ${STATUS_LABELS[task.status]}`}
        >
          <option value={task.status}>{STATUS_LABELS[task.status]}</option>
          {nextStatuses.map((s) => (
            <option key={s} value={s}>
              → {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        {canEdit && (
          <div className="flex shrink-0 gap-1">
            <Button variant="ghost" size="sm" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => deleteTask.mutate(task.id)}
              isLoading={deleteTask.isPending}
              className="text-danger hover:text-danger"
            >
              Delete
            </Button>
          </div>
        )}
      </div>

      {/* Mobile card */}
      <div className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-3 sm:hidden">
        <div className="flex items-start justify-between gap-2">
          <p className="text-body text-sm font-medium">{task.title}</p>
          <select
            value={task.status}
            onChange={(e) =>
              transition.mutate({
                taskId: task.id,
                status: e.target.value as TaskStatus,
                updatedAt: task.updated_at,
              })
            }
            className={`shrink-0 cursor-pointer rounded-full border px-2 py-0.5 text-xs font-medium outline-none ${STATUS_COLOURS[task.status]}`}
            aria-label={`Task status: ${STATUS_LABELS[task.status]}`}
          >
            <option value={task.status}>{STATUS_LABELS[task.status]}</option>
            {nextStatuses.map((s) => (
              <option key={s} value={s}>
                → {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className={`font-medium ${PRIORITY_COLOURS[task.priority]}`}>{task.priority}</span>
          {assigneeName && <span className="text-muted">{assigneeName}</span>}
          {task.due_date && <span className="text-muted">{formatDate(task.due_date)}</span>}
        </div>
        {canEdit && (
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => deleteTask.mutate(task.id)}
              isLoading={deleteTask.isPending}
            >
              Delete
            </Button>
          </div>
        )}
      </div>

      {editOpen && (
        <EditTaskDialog
          projectId={projectId}
          task={task}
          members={members}
          open={editOpen}
          onOpenChange={setEditOpen}
        />
      )}
    </>
  );
}

// ── Tasks tab ─────────────────────────────────────────────────────────────────

function TasksTab({
  projectId,
  members,
  currentUserId,
  isAdmin,
}: {
  projectId: string;
  members: MemberResponse[];
  currentUserId: string;
  isAdmin: boolean;
}) {
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useTasks(projectId);

  useCreateShortcut(() => setCreateOpen(true));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-muted text-sm">
          {data ? `${data.total} task${data.total !== 1 ? "s" : ""}` : ""}
        </p>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          Add task
        </Button>
      </div>

      {isLoading ? (
        <TaskListSkeleton />
      ) : !data?.items.length ? (
        <EmptyState
          icon="✅"
          title="No tasks yet"
          description="Add your first task to start tracking work."
          action={
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              Add task
            </Button>
          }
        />
      ) : (
        <div>
          {data.items.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              projectId={projectId}
              members={members}
              currentUserId={currentUserId}
              isAdmin={isAdmin}
            />
          ))}
          {data.total > data.items.length && (
            <p className="text-muted pt-2 text-center text-xs">
              +{data.total - data.items.length} more
            </p>
          )}
        </div>
      )}

      <CreateTaskDialog
        projectId={projectId}
        members={members}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}

// ── Members tab ───────────────────────────────────────────────────────────────

function InviteMemberDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const invite = useInviteMember(projectId);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteMemberFormData>({ resolver: zodResolver(inviteMemberSchema) });

  async function onSubmit(data: InviteMemberFormData) {
    await invite.mutateAsync(data);
    reset();
    onOpenChange(false);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) reset();
        onOpenChange(v);
      }}
      title="Invite member"
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="Email"
          type="email"
          placeholder="teammate@example.com"
          error={errors.email?.message}
          {...register("email")}
        />
        <Select label="Role" {...register("role")}>
          <option value="member">Member</option>
          <option value="admin">Admin</option>
        </Select>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" isLoading={invite.isPending}>
            Invite
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function MemberRow({
  member,
  projectId,
  currentUserId,
  isAdmin,
}: {
  member: MemberResponse;
  projectId: string;
  currentUserId: string;
  isAdmin: boolean;
}) {
  const changeRole = useChangeMemberRole(projectId);
  const remove = useRemoveMember(projectId);
  const isSelf = member.user_id === currentUserId;
  const canManage = isAdmin && !isSelf;

  return (
    <>
      {/* Desktop row */}
      <div className="border-border hidden items-center gap-3 border-b py-3 last:border-0 sm:flex">
        <div className="bg-primary/10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold uppercase">
          {member.user.name[0]}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-body text-sm font-medium">
            {member.user.name}
            {isSelf && <span className="text-muted ml-1 text-xs">(you)</span>}
          </p>
          <p className="text-muted truncate text-xs">{member.user.email}</p>
        </div>
        {canManage ? (
          <select
            value={member.role}
            onChange={(e) =>
              changeRole.mutate({ userId: member.user_id, role: e.target.value as ProjectRole })
            }
            className="border-border bg-surface cursor-pointer rounded-full border px-2.5 py-0.5 text-xs outline-none"
            aria-label={`Role for ${member.user.name}`}
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
        ) : (
          <span className="border-border bg-surface rounded-full border px-2.5 py-0.5 text-xs capitalize">
            {member.role}
          </span>
        )}
        {canManage && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => remove.mutate(member.user_id)}
            isLoading={remove.isPending}
            className="text-danger hover:text-danger"
          >
            Remove
          </Button>
        )}
      </div>

      {/* Mobile card */}
      <div className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-3 sm:hidden">
        <div className="flex items-center gap-3">
          <div className="bg-primary/10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold uppercase">
            {member.user.name[0]}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-body text-sm font-medium">
              {member.user.name}
              {isSelf && <span className="text-muted ml-1 text-xs">(you)</span>}
            </p>
            <p className="text-muted truncate text-xs">{member.user.email}</p>
          </div>
          <span className="border-border bg-surface rounded-full border px-2.5 py-0.5 text-xs capitalize">
            {member.role}
          </span>
        </div>
        {canManage && (
          <div className="flex gap-2">
            <select
              value={member.role}
              onChange={(e) =>
                changeRole.mutate({ userId: member.user_id, role: e.target.value as ProjectRole })
              }
              className="border-border bg-bg flex-1 rounded-md border px-2 py-1 text-xs outline-none"
              aria-label={`Role for ${member.user.name}`}
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
            <Button
              variant="danger"
              size="sm"
              onClick={() => remove.mutate(member.user_id)}
              isLoading={remove.isPending}
            >
              Remove
            </Button>
          </div>
        )}
      </div>
    </>
  );
}

function MembersTab({
  projectId,
  currentUserId,
  isAdmin,
}: {
  projectId: string;
  currentUserId: string;
  isAdmin: boolean;
}) {
  const [inviteOpen, setInviteOpen] = useState(false);
  const { data, isLoading } = useMembers(projectId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-muted text-sm">
          {data ? `${data.total} member${data.total !== 1 ? "s" : ""}` : ""}
        </p>
        {isAdmin && (
          <Button size="sm" onClick={() => setInviteOpen(true)}>
            Invite member
          </Button>
        )}
      </div>

      {isLoading ? (
        <MemberListSkeleton />
      ) : !data?.items.length ? (
        <EmptyState
          icon="👥"
          title="No members yet"
          description="Invite teammates to collaborate on this project."
          action={
            isAdmin ? (
              <Button size="sm" onClick={() => setInviteOpen(true)}>
                Invite member
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div>
          {data.items.map((m) => (
            <MemberRow
              key={m.id}
              member={m}
              projectId={projectId}
              currentUserId={currentUserId}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      )}

      {isAdmin && (
        <InviteMemberDialog projectId={projectId} open={inviteOpen} onOpenChange={setInviteOpen} />
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type Tab = "tasks" | "members";

export function ProjectDetailPage() {
  const { projectId = "" } = useParams<{ projectId: string }>();
  const [tab, setTab] = useState<Tab>("tasks");
  const [editOpen, setEditOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const currentUser = useAuthStore((s) => s.user);

  const { data: project, isLoading: projectLoading } = useProject(projectId);
  const { data: members } = useMembers(projectId);
  const updateProject = useUpdateProject(projectId);
  const deleteProject = useDeleteProject();

  const currentMember = useMemo(
    () => members?.items.find((m) => m.user_id === currentUser?.id),
    [members, currentUser],
  );
  const isAdmin = currentMember?.role === "admin";

  const {
    register: regEdit,
    handleSubmit: handleEdit,
    formState: { errors: editErrors },
  } = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
    values: project ? { name: project.name, description: project.description } : undefined,
  });

  async function onEditSubmit(data: CreateProjectFormData) {
    await updateProject.mutateAsync(data);
    setEditOpen(false);
  }

  if (projectLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-6 w-32" />
        <div className="space-y-2">
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-4 w-3/4" />
        </div>
        <TaskListSkeleton />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="p-6">
        <EmptyState
          icon="🔍"
          title="Project not found"
          description="This project doesn't exist or you don't have access."
          action={
            <Button asChild variant="secondary">
              <Link to="/projects">Back to projects</Link>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6 p-6">
        {/* Back link */}
        <Link to="/projects" className="text-muted hover:text-body flex items-center gap-1 text-sm">
          ← Projects
        </Link>

        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h1 className="text-body text-2xl font-semibold">{project.name}</h1>
            {project.description && (
              <p className="text-muted mt-1 text-sm">{project.description}</p>
            )}
          </div>
          {isAdmin && (
            <div className="flex shrink-0 gap-2">
              <Button variant="secondary" size="sm" onClick={() => setEditOpen(true)}>
                Edit
              </Button>
              <Button variant="danger" size="sm" onClick={() => setDeleteConfirm(true)}>
                Delete
              </Button>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="border-border border-b">
          <nav className="-mb-px flex gap-6" role="tablist">
            {(["tasks", "members"] as Tab[]).map((t) => (
              <button
                key={t}
                type="button"
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={`pb-3 text-sm font-medium capitalize transition-colors ${
                  tab === t
                    ? "border-primary text-primary border-b-2"
                    : "text-muted hover:text-body"
                }`}
              >
                {t}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab content */}
        <Card>
          <CardHeader>
            <CardTitle>{tab === "tasks" ? "Tasks" : "Members"}</CardTitle>
          </CardHeader>
          <CardContent>
            {tab === "tasks" ? (
              <TasksTab
                projectId={projectId}
                members={members?.items ?? []}
                currentUserId={currentUser?.id ?? ""}
                isAdmin={!!isAdmin}
              />
            ) : (
              <MembersTab
                projectId={projectId}
                currentUserId={currentUser?.id ?? ""}
                isAdmin={!!isAdmin}
              />
            )}
          </CardContent>
        </Card>

        {/* Edit project dialog */}
        <Dialog open={editOpen} onOpenChange={setEditOpen} title="Edit project">
          <form onSubmit={handleEdit(onEditSubmit)} noValidate className="flex flex-col gap-4">
            <Input label="Name" error={editErrors.name?.message} {...regEdit("name")} />
            <Textarea label="Description" {...regEdit("description")} />
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setEditOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" isLoading={updateProject.isPending}>
                Save
              </Button>
            </div>
          </form>
        </Dialog>

        {/* Delete confirmation dialog */}
        <Dialog open={deleteConfirm} onOpenChange={setDeleteConfirm} title="Delete project">
          <div className="space-y-4">
            <p className="text-muted text-sm">
              Are you sure you want to delete <strong className="text-body">{project.name}</strong>?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setDeleteConfirm(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => deleteProject.mutate(project.id)}
                isLoading={deleteProject.isPending}
              >
                Delete
              </Button>
            </div>
          </div>
        </Dialog>
      </div>
    </ErrorBoundary>
  );
}
