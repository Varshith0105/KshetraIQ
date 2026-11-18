"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function PlantIntelligenceRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    // Automatically redirect to the unified Plant Disease & Intelligence workspace
    router.replace("/dashboard?view=disease");
  }, [router]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#f8faf8",
        padding: 24,
        textAlign: "center",
      }}
    >
      <div
        style={{
          background: "white",
          padding: 36,
          borderRadius: 16,
          border: "1px solid #c9ddcc",
          maxWidth: 540,
          boxShadow: "0 6px 20px rgba(0,0,0,0.06)",
        }}
      >
        <span style={{ fontSize: "40px", display: "block", marginBottom: 12 }}>🌿</span>
        <h2 style={{ fontSize: "1.4rem", fontWeight: 700, color: "#166534", margin: "0 0 10px 0" }}>
          Plant Intelligence is Integrated
        </h2>
        <p style={{ fontSize: "0.9rem", color: "#4b5563", lineHeight: 1.5, margin: "0 0 20px 0" }}>
          All research models (ResNet50, SAM, LIME, and BLIP) are now unified inside the
          <strong> Plant Disease</strong> page. You do not need to navigate to a separate screen.
        </p>
        <Link
          href="/dashboard?view=disease"
          style={{
            display: "inline-block",
            padding: "12px 24px",
            background: "#166534",
            color: "white",
            borderRadius: 8,
            textDecoration: "none",
            fontWeight: 600,
            fontSize: "0.9rem",
          }}
        >
          Open Plant Disease Workspace →
        </Link>
      </div>
    </div>
  );
}
