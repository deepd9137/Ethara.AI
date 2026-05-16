import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { Button, Card, Input } from "@/components/ui";
import { useToast } from "@/components/ui/useToast";
import { parseApiError } from "@/lib/api/errors";
import { useSignup } from "../hooks";
import { signupSchema, type SignupFormData } from "../schemas";

export function SignupPage() {
  const { toast } = useToast();
  const signup = useSignup();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
  });

  async function onSubmit(data: SignupFormData) {
    try {
      await signup.mutateAsync(data);
    } catch (err) {
      const { message } = parseApiError(err);
      toast({ variant: "error", title: "Sign up failed", description: message });
    }
  }

  return (
    <div className="bg-bg flex min-h-screen items-center justify-center px-4">
      <main className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-body text-2xl font-semibold">Create an account</h1>
          <p className="text-muted mt-1 text-sm">Start managing your projects today</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-4">
            <Input
              label="Name"
              type="text"
              autoComplete="name"
              error={errors.name?.message}
              {...register("name")}
            />
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
              autoComplete="new-password"
              error={errors.password?.message}
              {...register("password")}
            />
            <Button type="submit" isLoading={signup.isPending} className="mt-2 w-full">
              Create account
            </Button>
          </form>
        </Card>

        <p className="text-muted mt-4 text-center text-sm">
          Already have an account?{" "}
          <Link to="/login" className="text-primary underline">
            Sign in
          </Link>
        </p>
      </main>
    </div>
  );
}
