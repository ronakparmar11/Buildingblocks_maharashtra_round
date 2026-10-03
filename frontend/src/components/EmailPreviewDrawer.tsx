import { useState } from "react";
import { useNotificationPreview } from "../api/hooks";
import { Drawer, ErrorState, Skeleton } from "./ui";

export default function EmailPreviewDrawer({
  notificationId,
  onClose,
}: {
  notificationId?: string;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"email" | "text">("email");
  const preview = useNotificationPreview(notificationId);
  return (
    <Drawer open={Boolean(notificationId)} title="Email preview" onClose={onClose}>
      {preview.isLoading ? (
        <Skeleton className="h-96" />
      ) : preview.isError || !preview.data ? (
        <ErrorState onRetry={() => preview.refetch()} />
      ) : (
        <>
          <p className="mb-4 font-medium">{preview.data.subject}</p>
          <div className="mb-4 flex border-b border-rule">
            {(["email", "text"] as const).map((item) => (
              <button
                key={item}
                onClick={() => setTab(item)}
                className={`border-b-2 px-4 py-2 text-sm ${tab === item ? "border-ink text-ink" : "border-transparent text-graphite"}`}
              >
                {item === "email" ? "Email" : "Plain text"}
              </button>
            ))}
          </div>
          {tab === "email" ? (
            <iframe
              title="Email content"
              sandbox=""
              srcDoc={preview.data.html}
              className="h-[560px] w-full border border-rule bg-white"
            />
          ) : (
            <pre className="whitespace-pre-wrap border border-rule bg-paper p-4 font-mono text-xs">
              {preview.data.text}
            </pre>
          )}
        </>
      )}
    </Drawer>
  );
}