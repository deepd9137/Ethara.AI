import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "./Button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  requestId: string | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, requestId: null };
  }

  static getDerivedStateFromError(error: Error): State {
    const axiosError = error as unknown as {
      response?: { headers?: Record<string, string> };
    };
    const requestId = axiosError?.response?.headers?.["x-request-id"] ?? null;
    return { hasError: true, error, requestId };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div role="alert" className="flex flex-col items-center gap-4 py-16 text-center">
          <div className="text-danger text-5xl" aria-hidden="true">
            ⚠
          </div>
          <div className="space-y-1">
            <p className="text-body font-semibold">Something went wrong</p>
            <p className="text-muted text-sm">
              {this.state.error?.message ?? "An unexpected error occurred"}
            </p>
            {this.state.requestId && (
              <p className="text-muted font-mono text-xs">Request ID: {this.state.requestId}</p>
            )}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => this.setState({ hasError: false, error: null, requestId: null })}
          >
            Try again
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
