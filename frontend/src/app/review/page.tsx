"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export default function ReviewPage() {
  const router = useRouter();
  const { user } = useAuth();

  useEffect(() => {
    if (!user) return;
    const capabilities = user.capabilities;
    if (capabilities.includes("bundle.review")) {
      router.replace("/review/analyses");
    } else if (capabilities.includes("output.review")) {
      router.replace("/review/outputs");
    } else {
      router.replace("/");
    }
  }, [user, router]);

  return <div className="card empty-state">Redirecting...</div>;
}
