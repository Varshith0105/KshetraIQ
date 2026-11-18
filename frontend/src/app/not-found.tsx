import Link from "next/link";

export default function NotFound() {
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
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          background: "white",
          padding: 36,
          borderRadius: 16,
          border: "1px solid #c9ddcc",
          maxWidth: 480,
          boxShadow: "0 6px 20px rgba(0,0,0,0.06)",
        }}
      >
        <span style={{ fontSize: "48px", display: "block", marginBottom: 12 }}>🌱</span>
        <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#166534", margin: "0 0 10px 0" }}>
          404 — Page Not Found
        </h2>
        <p style={{ fontSize: "0.9rem", color: "#4b5563", lineHeight: 1.5, margin: "0 0 24px 0" }}>
          The page or resource you requested could not be found in KshetraIQ.
        </p>
        <Link
          href="/dashboard"
          style={{
            display: "inline-block",
            padding: "10px 20px",
            background: "#166534",
            color: "white",
            borderRadius: 8,
            textDecoration: "none",
            fontWeight: 600,
            fontSize: "0.9rem",
          }}
        >
          Return to Dashboard →
        </Link>
      </div>
    </div>
  );
}
