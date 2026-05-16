import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { Button, Card, Input } from "@/components/ui";
import { useToast } from "@/components/ui/useToast";
import { parseApiError } from "@/lib/api/errors";
import { useLogin } from "../hooks";
import { loginSchema, type LoginFormData } from "../schemas";

export function LoginPage() {
  const [searchParams] = useSearchParams();
  const { toast } = useToast();
  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: searchParams.get("email") ?? "" },
  });

  async function onSubmit(data: LoginFormData) {
    try {
      await login.mutateAsync(data);
    } catch (err) {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Login failed", description: message });
    }
  }

  return (
    <div className="bg-bg flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-body text-2xl font-semibold">Welcome back</h1>
          <p className="text-muted mt-1 text-sm">Sign in to your account</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Input
              label="Email"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              {...register("email")}
            />
            <Input
              label="Password"
              type="password"
              autoComplete="current-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <Button type="submit" isLoading={login.isPending} className="mt-2 w-full">
              Sign in
            </Button>
          </form>
        </Card>

        <p className="text-muted mt-4 text-center text-sm">
          Don&apos;t have an account?{" "}
          <Link to="/signup" className="text-primary hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
