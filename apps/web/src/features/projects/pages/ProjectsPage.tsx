import { useState } from "react";
import { Link } from "react-router-dom";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import {
  Button,
  Card,
  CardContent,
  Dialog,
  EmptyState,
  Input,
  ProjectListSkeleton,
  Textarea,
} from "@/components/ui";
import { useCreateShortcut } from "@/lib/hooks/useKeyboardShortcuts";
import { useCreateProject, useProjects } from "../hooks";
import { createProjectSchema, type CreateProjectFormData } from "../schemas";

function ProjectCard({
  project,
}: {
  project: { id: string; name: string; description: string; created_at: string };
}) {
  return (
    <Card className="flex flex-col gap-2 transition-shadow hover:shadow-md">
      <CardContent className="pt-0">
        <div className="flex flex-col gap-1">
          <h2 className="text-body truncate font-semibold">{project.name}</h2>
          {project.description ? (
            <p className="text-muted line-clamp-2 text-sm">{project.description}</p>
          ) : (
            <p className="text-muted text-sm italic">No description</p>
          )}
          <p className="text-muted mt-1 text-xs">
            Created {new Date(project.created_at).toLocaleDateString()}
          </p>
        </div>
        <div className="mt-3">
          <Button asChild variant="secondary" size="sm">
            <Link to={`/projects/${project.id}`}>Open project</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function CreateProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const create = useCreateProject();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateProjectFormData>({
    resolver: zodResolver(createProjectSchema),
  });

  async function onSubmit(data: CreateProjectFormData) {
    await create.mutateAsync(data);
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
      title="New project"
    >
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
        <Input
          label="Name"
          placeholder="e.g. Marketing website"
          error={errors.name?.message}
          {...register("name")}
        />
        <Textarea
          label="Description"
          placeholder="What's this project about? (optional)"
          error={errors.description?.message}
          {...register("description")}
        />
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

export function ProjectsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading } = useProjects();

  useCreateShortcut(() => setCreateOpen(true));

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-body text-2xl font-semibold">Projects</h1>
          <p className="text-muted mt-1 text-sm">All projects you belong to</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>New project</Button>
      </div>

      {isLoading ? (
        <ProjectListSkeleton />
      ) : !data?.items.length ? (
        <EmptyState
          icon="📁"
          title="No projects yet"
          description="Create your first project to start tracking tasks with your team."
          action={<Button onClick={() => setCreateOpen(true)}>Create a project</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.items.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}

      <CreateProjectDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  );
}
