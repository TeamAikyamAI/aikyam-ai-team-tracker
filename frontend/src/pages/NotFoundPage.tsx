import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";
import { CompassIcon } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <EmptyState
        icon={<CompassIcon className="h-6 w-6" />}
        title="Page not found"
        description="The page you're looking for doesn't exist or may have moved."
        action={
          <Button asChild>
            <Link to="/">Back to dashboard</Link>
          </Button>
        }
      />
    </div>
  );
}
