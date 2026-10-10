import Link from "next/link";
import { FileQuestion } from "lucide-react";
import { buttonClass } from "./ui/button";
import { Card } from "./ui/card";
import { EmptyState } from "./ui/empty-state";

export function NotFoundState({
  title,
  description,
  href,
  linkLabel,
}: {
  title: string;
  description: string;
  href: string;
  linkLabel: string;
}) {
  return (
    <Card className="mx-auto mt-8 max-w-lg">
      <EmptyState
        icon={FileQuestion}
        title={title}
        description={description}
        action={
          <Link href={href} className={buttonClass("secondary", "sm")}>
            {linkLabel}
          </Link>
        }
      />
    </Card>
  );
}

export function PatientNotFound() {
  return (
    <NotFoundState
      title="Patient not found"
      description="This patient doesn't exist or has been deleted. Deleted patients no longer appear in the console."
      href="/patients/"
      linkLabel="Back to patients"
    />
  );
}

export function CallNotFound() {
  return (
    <NotFoundState
      title="Call not found"
      description="This call record doesn't exist. Check the link and try again."
      href="/calls/"
      linkLabel="Back to calls"
    />
  );
}
